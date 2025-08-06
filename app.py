import streamlit as st
import pandas as pd
import os
import time
import io
from datetime import datetime
from openpyxl import load_workbook

EXCEL_FILE = "Updated_Stock_Data.xlsx"
SHEET_NAME = 0
LOG_SHEET_NAME = "Operation_Log"

# تحميل بيانات المنتجات
@st.cache_data
def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, engine="openpyxl")
        df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
        df["in"] = pd.to_numeric(df["in"], errors="coerce")
        df["out"] = pd.to_numeric(df["out"], errors="coerce")
        df["current_balance"] = df["in"].fillna(0) - df["out"].fillna(0)
        return df
    else:
        cols = ["Stock Code", "Description", "code num", "in", "out", "Unit", "Qty", "LOCATION"]
        df = pd.DataFrame(columns=cols)
        df.to_excel(EXCEL_FILE, index=False)
        return df

# حفظ بيانات المنتجات
def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

# تحميل أو تهيئة سجل العمليات
def load_operation_log():
    if os.path.exists(EXCEL_FILE):
        try:
            df_log = pd.read_excel(EXCEL_FILE, sheet_name=LOG_SHEET_NAME, engine="openpyxl")
        except:
            df_log = pd.DataFrame(columns=["Timestamp", "Barcode", "Description", "Operation", "Quantity"])
    else:
        df_log = pd.DataFrame(columns=["Timestamp", "Barcode", "Description", "Operation", "Quantity"])
    return df_log

# حفظ السجل
def save_operation_log(df_log):
    book = load_workbook(EXCEL_FILE)
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        writer.book = book
        df_log.to_excel(writer, sheet_name=LOG_SHEET_NAME, index=False)

# البحث عن منتج
def find_item(df, code):
    return df[df["code num"].astype(str) == code]

# تحويل البيانات إلى Excel للتحميل
@st.cache_data
def convert_df_to_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

# ========= التطبيق =========
def main():
    st.set_page_config(page_title="Warehouse System", layout="wide")
    st.title("📦 Warehouse System with Barcode, Excel, and Logging")

    # منع العمليات المتعددة في نفس الوقت
    if "operation_in_progress" not in st.session_state:
        st.session_state["operation_in_progress"] = False
    if "current_code" not in st.session_state:
        st.session_state["current_code"] = ""

    df = load_data()
    df_log = load_operation_log()

    # ----------- عرض البيانات الكاملة وتحميلها ----------
    with st.expander("📋 عرض البيانات الكاملة"):
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="⬇️ تحميل كل البيانات Excel",
            data=convert_df_to_excel(df),
            file_name="all_warehouse_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ----------- الفلاتر والتحليل ----------
    st.sidebar.header("🔍 فلترة")
    locations = df["LOCATION"].dropna().unique().tolist()
    units = df["Unit"].dropna().unique().tolist()
    selected_location = st.sidebar.selectbox("اختر الموقع", ["كل المواقع"] + locations)
    selected_unit = st.sidebar.selectbox("اختر الوحدة", ["كل الوحدات"] + units)

    df_filtered = df.copy()
    if selected_location != "كل المواقع":
        df_filtered = df_filtered[df_filtered["LOCATION"] == selected_location]
    if selected_unit != "كل الوحدات":
        df_filtered = df_filtered[df_filtered["Unit"] == selected_unit]

    st.subheader("📊 ملخص وتحليل البيانات")
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 عدد المنتجات", len(df_filtered))
    col2.metric("📍 عدد المواقع", df_filtered["LOCATION"].nunique())
    col3.metric("🧮 عدد الوحدات", df_filtered["Unit"].nunique())
    col4, col5, col6 = st.columns(3)
    col4.metric("📥 إجمالي الإدخال", int(df_filtered["in"].sum(skipna=True)))
    col5.metric("📤 إجمالي الإخراج", int(df_filtered["out"].sum(skipna=True)))
    col6.metric("📦 إجمالي الكمية", int(df_filtered["Qty"].sum(skipna=True)))
    st.subheader("📍 الكمية حسب الموقع")
    st.bar_chart(df_filtered.groupby("LOCATION")["Qty"].sum())
    st.subheader("🧮 الكمية حسب نوع الوحدة")
    st.bar_chart(df_filtered.groupby("Unit")["Qty"].sum())
    st.subheader("🔝 أعلى العناصر حسب الكمية")
    st.dataframe(df_filtered.sort_values(by="Qty", ascending=False)[["Description", "Qty"]].head(10))
    st.download_button(
        label="⬇️ تحميل البيانات المصفّاة Excel",
        data=convert_df_to_excel(df_filtered),
        file_name="filtered_warehouse_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ----------- سجل العمليات ----------
    with st.expander("📜 سجل العمليات"):
        st.dataframe(df_log.tail(50), use_container_width=True)
        st.download_button(
            label="⬇️ تحميل سجل العمليات Excel",
            data=convert_df_to_excel(df_log),
            file_name="operation_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ----------- إدخال الكود يدويًا/باركود -----------
    st.subheader("📥 إدخال كود المنتج يدويًا أو باستخدام قارئ الباركود")
    barcode_input = st.text_input("🔎 أدخل أو امسح الباركود هنا", key="barcode_input")

    if barcode_input:
        code = barcode_input.strip()
        if st.session_state["operation_in_progress"] and st.session_state["current_code"] != code:
            st.warning("يرجى إنهاء العملية الحالية قبل البدء بعملية جديدة.")
            return

        match = find_item(df, code)

        if not match.empty:
            st.info("✅ العنصر موجود:")
            st.dataframe(match)
            with st.form(f"form_{code}_{int(time.time())}"):
                operation = st.radio("العملية:", ["إدخال", "إخراج"])
                quantity = st.number_input("الكمية", min_value=1, value=1)
                confirm = st.checkbox("هل تريد تنفيذ العملية؟")
                submitted = st.form_submit_button("تأكيد")

                if submitted:
                    if not confirm:
                        st.warning("يجب تأكيد تنفيذ العملية أولاً.")
                        return
                    st.session_state["operation_in_progress"] = True
                    st.session_state["current_code"] = code
                    idx = match.index[0]
                    desc = match.iloc[0]["Description"]
                    if operation == "إدخال":
                        df.at[idx, "in"] = (df.at[idx, "in"] if pd.notna(df.at[idx, "in"]) else 0) + quantity
                    else:
                        df.at[idx, "out"] = (df.at[idx, "out"] if pd.notna(df.at[idx, "out"]) else 0) + quantity
                    save_data(df)
                    # تسجيل في السجل
                    log_entry = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Barcode": code,
                        "Description": desc,
                        "Operation": operation,
                        "Quantity": quantity
                    }
                    df_log = pd.concat([df_log, pd.DataFrame([log_entry])], ignore_index=True)
                    save_operation_log(df_log)
                    st.success("✅ تم تحديث الكمية وتسجيل العملية بنجاح.")
                    st.dataframe(find_item(df, code))
                    st.session_state["operation_in_progress"] = False
                    st.session_state["current_code"] = ""

        else:
            st.warning("❗ الكود غير موجود. الرجاء إدخال معلوماته:")
            with st.form(f"new_form_{code}_{int(time.time())}"):
                stock_code = st.text_input("Stock Code")
                desc = st.text_input("Description")
                unit = st.text_input("Unit")
                qty = st.number_input("Qty", min_value=0)
                location = st.text_input("LOCATION")
                confirm = st.checkbox("هل تريد إضافة المنتج؟")
                submitted = st.form_submit_button("حفظ")
                if submitted:
                    if not confirm:
                        st.warning("يجب تأكيد إضافة المنتج أولاً.")
                        return
                    st.session_state["operation_in_progress"] = True
                    st.session_state["current_code"] = code
                    new_row = {
                        "Stock Code": stock_code,
                        "Description": desc,
                        "code num": code,
                        "in": 0,
                        "out": 0,
                        "Unit": unit,
                        "Qty": qty,
                        "LOCATION": location
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)
                    log_entry = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Barcode": code,
                        "Description": desc,
                        "Operation": "إضافة منتج جديد",
                        "Quantity": qty
                    }
                    df_log = pd.concat([df_log, pd.DataFrame([log_entry])], ignore_index=True)
                    save_operation_log(df_log)
                    st.success("✅ تم حفظ المنتج الجديد وتسجيل العملية.")
                    st.dataframe(find_item(df, code))
                    st.session_state["operation_in_progress"] = False
                    st.session_state["current_code"] = ""

if __name__ == "__main__":
    main()
