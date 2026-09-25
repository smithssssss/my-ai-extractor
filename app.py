import streamlit as st
import requests
import json
import pandas as pd
import os

# ================= 1. 页面配置 =================
st.set_page_config(page_title="文献摘要提取器", layout="wide")
st.title("🧪 文献摘要信息提取器")
st.markdown("输入文献摘要，AI 自动提取【实验条件】和【结论】，并支持一键导出 Excel。")

# ================= 2. 你的核心 API 逻辑 (记得填入真实的 API_KEY) =================
#API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 建议后续改为从环境变量读取
# 优先从云端 Secrets 读取，本地测试再从环境变量读取
if "DEEPSEEK_API_KEY" in st.secrets:
    API_KEY = st.secrets["DEEPSEEK_API_KEY"]
else:
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/chat/completions"  # 如果是DeepSeek就填这个


def extract_from_abstract(abstract_text):
    system_prompt = """
    你是一个资深的化学材料研发专家。你需要阅读用户提供的文献摘要。
    请严格提取出以下两个维度的信息：
    1、实验条件（包含：温度、反应时间、催化剂/试剂、配比等关键参数，如果没有则填“未提及”）
    2、结论（提炼核心研究成果、材料性能或机理发现）

    你必须以合法且干净的 JSON 格式输出，不要带任何 markdown 格式（如 ```json），不要任何多余的解释。
    格式示例：
    {
      "实验条件": "温度: 80°C; 反应时间: 12小时; 催化剂: 5% Pt/C",
      "结论": "该催化剂在低温下展现出优异的转化率，达到95%。"
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": "deepseek-chat",  # 根据你实际使用的模型修改，如 deepseek-flash 或 deepseek-chat
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": abstract_text}
        ],
        "temperature": 0.1,  # 降低随机性，确保格式稳定
        "response_format": {"type": "json_object"}  # 强制API返回JSON（如果API支持）
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()  # 检查网络错误
        result_text = response.json()['choices'][0]['message']['content']
        return result_text
    except Exception as e:
        return f"请求发生错误: {str(e)}"


# ================= 3. Streamlit 界面组件 =================
# 文本输入框
input_text = st.text_area("📄 请粘贴文献摘要：", height=200, placeholder="在这里输入或粘贴待提取的摘要内容...")

# 按钮触发
if st.button("🚀 开始提取", type="primary"):
    if not input_text.strip():
        st.warning("请先输入文献摘要！")
    else:
        with st.spinner("AI 正在阅读并提取信息，请稍候..."):
            # 调用你的核心函数
            raw_result = extract_from_abstract(input_text)

            # 处理大模型可能带上的 ```json 标记
            clean_result = raw_result.replace("```json", "").replace("```", "").strip()

            try:
                # 解析 JSON 字符串为 Python 字典
                data = json.loads(clean_result)

                st.success("提取完成！")

                # 展示结果 (两列布局)
                col1, col2 = st.columns(2)
                with col1:
                    st.info("【实验条件】")
                    st.write(data.get("实验条件", "未提及"))
                with col2:
                    st.success("【结论】")
                    st.write(data.get("结论", "未提及"))

                # 导出 Excel 的功能
                st.markdown("---")
                st.subheader("📥 导出数据")
                # 把字典转为 DataFrame，再转为 Excel 字节流
                df = pd.DataFrame([data])
                excel_data = df.to_excel(index=False, engine='openpyxl')  # 需要 pip install openpyxl

                st.download_button(
                    label="点击下载 Excel 文件",
                    data=excel_data,
                    file_name="extraction_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except json.JSONDecodeError:
                st.error("大模型返回的格式不是标准 JSON，解析失败。原始返回内容如下：")
                st.code(clean_result)