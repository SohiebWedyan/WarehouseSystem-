import streamlit as st
import pandas as pd
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import os
import time
import io

# المكوّن الجديد للبث المستمر من الكاميرا
from camera_input_live import camera_input_live

EXCEL_FILE = "Updated_Stock_Data.xlsx"
SHEET_NAME = 0

@st.cache_data
def load_data(file=None):
    """تحميل البيانات من ملف مرفوع أو محلي"""
    if file is not None:
        df = pd.read_excel(file, sheet_name=SHEET_NAME, engine="openpyxl")
    elif os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, engine="openpyxl")
    else:
        cols = ["Stock Code", "Description", "code num", "in", "out", "Unit", "Qty", "LOCATION"]
        df = pd.DataFrame(columns=cols)
        df.to_excel(EXCEL_FILE, index=False)
        return df

    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["in"] = pd.to_numeric(df["in"], errors="coerce")
    df["out"] = pd.to_numeric(df["out"], errors="coerce")
    df["current_balance"] = df["in"].fillna(0) - df["out"].fillna(0)
    return df

def save_data(df):
    """حفظ البيانات في ملف إكسل محلي"""
    df.to_excel(EXCEL_FILE, index=False)

def find_item(df, code):
    """البحث عن منتج بحسب رقم الكود"""
    return df[df["code num"].astype(str) == code]

@st.cache_data
def convert_df_to_excel(dataframe):
    """تحويل الداتا فريم إلى ملف إكسل"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

def main():
    st.set_page_config(page_title="Warehouse System", layout="wide")
    st.title("📦 Warehouse System with Barcode, Excel, and Analytics")

    # اختيار ملف إكسل من المستخدم
    uploaded_file = st.sidebar.file_uploader("⬆️ رفع ملف Excel", type=["xlsx"])

    # تحميل البيانات
    df = load_data(uploaded_file)

    # عرض البيانات الكاملة
    with st.expander("📋 عرض البيانات الكاملة"):
        st.dataframe(df, use_container_width=True)

    # فلاتر جانبية
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

    # ملخص وتحليل البيانات
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

    # زر تحميل البيانات المصفاة
    st.download_button(
        label="⬇️ تحميل البيانات Excel",
        data=convert_df_to_excel(df_filtered),
        file_name="filtered_warehouse_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # تحضير session_state لمنع التكرار
    if 'last_scanned' not in st.session_state:
        st.session_state['last_scanned'] = ""
    if 'last_time' not in st.session_state:
        st.session_state['last_time'] = 0

    # البث المباشر باستخدام camera_input_live
    st.subheader("📷 الكاميرا في الوقت الحقيقي لإدخال أو إخراج المنتجات")
    run_camera = st.checkbox("تشغيل الكاميرا (بث مباشر)", value=False)

    if run_camera:
        # debounce بـ 500 ميلي ثانية لضبط سرعة التحديث (يمكنك تعديلها)
        image = camera_input_live(debounce=500, show_controls=True,
                                  start_label="بدء الالتقاط", stop_label="إيقاف الالتقاط")

        if image is not None:
            # تحويل BytesIO إلى مصفوفة OpenCV
            bytes_data = image.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

            # قراءة الباركود أو QR
            barcodes = decode(cv2_img)
            for barcode in barcodes:
                code = barcode.data.decode("utf-8")
                # منع التكرار السريع
                if code != st.session_state['last_scanned'] or \
                   time.time() - st.session_state['last_time'] > 3:
                    st.session_state['last_scanned'] = code
                    st.session_state['last_time'] = time.time()

                    st.success(f"📥 تم قراءة الكود: `{code}`")
                    match = find_item(df, code)

                    if not match.empty:
                        st.info("✅ العنصر موجود:")
                        st.dataframe(match)

                        with st.form(f"form_{code}"):
                            operation = st.radio("العملية:", ["إدخال", "إخراج"])
                            quantity = st.number_input("الكمية", min_value=1, value=1)
                            submitted = st.form_submit_button("تأكيد")

                            if submitted:
                                idx = match.index[0]
                                if operation == "إدخال":
                                    df.at[idx, "in"] = (df.at[idx, "in"] if pd.notna(df.at[idx, "in"]) else 0) + quantity
                                else:
                                    df.at[idx, "out"] = (df.at[idx, "out"] if pd.notna(df.at[idx, "out"]) else 0) + quantity
                                # حفظ التغييرات إذا لم يكن الملف مرفوعًا
                                if uploaded_file is None:
                                    save_data(df)
                                updated_row = find_item(df, code)
                                st.success("✅ تم تحديث الكمية بنجاح.")
                                st.dataframe(updated_row)

                    else:
                        st.warning("❗ الكود غير موجود. الرجاء إدخال معلوماته:")
                        with st.form(f"new_form_{code}"):
                            stock_code = st.text_input("Stock Code")
                            desc = st.text_input("Description")
                            unit = st.text_input("Unit")
                            qty = st.number_input("Qty", min_value=0)
                            location = st.text_input("LOCATION")
                            submitted = st.form_submit_button("حفظ")

                            if submitted:
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
                                if uploaded_file is None:
                                    save_data(df)
                                st.success("✅ تم حفظ المنتج الجديد.")
                                st.dataframe(find_item(df, code))

if __name__ == "__main__":
    main()
