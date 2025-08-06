import streamlit as st
import pandas as pd
import os
import time
import io



EXCEL_FILE = "Updated_Stock_Data.xlsx"
SHEET_NAME = 0  # يمكن تغييرها إذا كان اسم الورقة مختلفًا


@st.cache_data
def load_data(file=None):
    """تحميل البيانات من ملف Excel. إذا تم تقديم ملف مرفوع، يستخدمه مباشرة.
    إذا لم يُرفع ملف ويُوجد ملف ثابت محلي، يُقرأ منه. وإلا يتم إنشاء
    ملف جديد بأعمدة افتراضية."""
    if file is not None:
        df = pd.read_excel(file, sheet_name=SHEET_NAME, engine="openpyxl")
    elif os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, engine="openpyxl")
    else:
        cols = ["Stock Code", "Description", "code num", "in", "out", "Unit", "Qty", "LOCATION"]
        df = pd.DataFrame(columns=cols)
        df.to_excel(EXCEL_FILE, index=False)
        return df

    # تحويل الأعمدة الرقمية للتأكد من العمليات الحسابية
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["in"] = pd.to_numeric(df["in"], errors="coerce")
    df["out"] = pd.to_numeric(df["out"], errors="coerce")
    df["current_balance"] = df["in"].fillna(0) - df["out"].fillna(0)
    return df


def save_data(df):
    """يحفظ إطار البيانات في الملف المحلي فقط عند عدم استخدام ملف مرفوع."""
    df.to_excel(EXCEL_FILE, index=False)


def find_item(df, code):
    """إرجاع الصفوف التي تطابق قيمة code في عمود 'code num'."""
    return df[df["code num"].astype(str) == code]


@st.cache_data
def convert_df_to_excel(dataframe):
    """تحويل إطار بيانات إلى ملف Excel في الذاكرة لإمكانية التحميل."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()


def main():
    st.set_page_config(page_title="Warehouse System", layout="wide")
    st.title("📦 Warehouse System with Barcode, Excel, and Analytics")

    # عنصر رفع ملف في الشريط الجانبي
    uploaded_file = st.sidebar.file_uploader("⬆️ رفع ملف Excel", type=["xlsx"])

    # تحميل البيانات من الملف المرفوع أو الملف الثابت
    df = load_data(uploaded_file)

    # إذا لم يتم تعريف متغيرات الحالة، نقوم بتعيينها
    # يستخدم operation_in_progress لمنع بدء عملية جديدة قبل انتهاء الحالية
    # current_code يحتفظ بالكود الجاري معالجته
    if "operation_in_progress" not in st.session_state:
        st.session_state["operation_in_progress"] = False
    if "current_code" not in st.session_state:
        st.session_state["current_code"] = None

    # ------- عرض البيانات الكاملة وتحميلها -------
    with st.expander("📋 عرض البيانات الكاملة"):
        st.dataframe(df, use_container_width=True)
        # زر لتحميل كل البيانات
        st.download_button(
            label="⬇️ تحميل كل البيانات Excel",
            data=convert_df_to_excel(df),
            file_name="all_warehouse_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ------- فلاتر جانبية -------
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

    # ------- ملخص وتحليل -------
    st.subheader("📊 ملخص وتحليل البيانات")
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 عدد المنتجات", len(df_filtered))
    col2.metric("📍 عدد المواقع", df_filtered["LOCATION"].nunique())
    col3.metric("🧮 عدد الوحدات", df_filtered["Unit"].nunique())

    col4, col5, col6 = st.columns(3)
    col4.metric("📥 إجمالي الإدخال", int(df_filtered["in"].sum(skipna=True)))
    col5.metric("📤 إجمالي الإخراج", int(df_filtered["out"].sum(skipna=True)))
    col6.metric("📦 إجمالي الكمية", int(df_filtered["Qty"].sum(skipna=True)))

    # رسوم بيانية بسيطة
    st.subheader("📍 الكمية حسب الموقع")
    st.bar_chart(df_filtered.groupby("LOCATION")["Qty"].sum())

    st.subheader("🧮 الكمية حسب نوع الوحدة")
    st.bar_chart(df_filtered.groupby("Unit")["Qty"].sum())

    st.subheader("🔝 أعلى العناصر حسب الكمية")
    st.dataframe(df_filtered.sort_values(by="Qty", ascending=False)[["Description", "Qty"]].head(10))

    # زر تحميل البيانات المصفاة
    st.download_button(
        label="⬇️ تحميل البيانات المصفّاة Excel",
        data=convert_df_to_excel(df_filtered),
        file_name="filtered_warehouse_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ------- إدخال الكود يدويًا أو عبر قارئ الباركود -------
    st.subheader("📥 إدخال كود المنتج يدويًا أو باستخدام جهاز قارئ الباركود")
    barcode_input = st.text_input("🔎 أدخل أو امسح الباركود هنا", key="barcode_input").strip()

    if barcode_input:
        code = barcode_input
        # إذا كانت هناك عملية أخرى قيد التنفيذ وترغب بمعالجة كود آخر، نُوقف التنفيذ
        if st.session_state.get("operation_in_progress", False) and st.session_state.get("current_code") != code:
            st.warning("⚠️ هناك عملية قيد التنفيذ. يرجى إكمالها أو إلغاؤها قبل البدء بعملية جديدة.")
        else:
            # ضبط الحالة بأن هناك عملية جارية لهذا الكود
            st.session_state["operation_in_progress"] = True
            st.session_state["current_code"] = code
            match = find_item(df, code)

            if not match.empty:
                # المنتج موجود
                st.info("✅ العنصر موجود:")
                st.dataframe(match)
                # نموذج لإجراء التحديث مع طلب تأكيد من المستخدم
                form_key = f"form_{code}_{int(time.time())}"
                with st.form(form_key):
                    operation = st.radio("العملية:", ["إدخال", "إخراج"])
                    quantity = st.number_input("الكمية", min_value=1, value=1)
                    confirm = st.radio("هل تريد تنفيذ التحديث وحفظه؟", ["نعم", "لا"])
                    submitted = st.form_submit_button("تأكيد")
                    if submitted:
                        if confirm == "نعم":
                            idx = match.index[0]
                            if operation == "إدخال":
                                df.at[idx, "in"] = (df.at[idx, "in"] if pd.notna(df.at[idx, "in"]) else 0) + quantity
                            else:
                                df.at[idx, "out"] = (df.at[idx, "out"] if pd.notna(df.at[idx, "out"]) else 0) + quantity
                            # حفظ التغييرات في الملف المحلي فقط إذا لم يكن هناك ملف مرفوع
                            if uploaded_file is None:
                                save_data(df)
                            updated_row = find_item(df, code)
                            st.success("✅ تم تحديث الكمية بنجاح.")
                            st.dataframe(updated_row)
                        else:
                            st.info("❎ تم إلغاء العملية. لم يتم تحديث أي قيمة.")
                        # في جميع الأحوال ننهي العملية الحالية
                        st.session_state["operation_in_progress"] = False
                        st.session_state["current_code"] = None

            else:
                # المنتج غير موجود: إدخال بيانات المنتج الجديد
                st.warning("❗ الكود غير موجود. الرجاء إدخال معلوماته:")
                new_form_key = f"new_form_{code}_{int(time.time())}"
                with st.form(new_form_key):
                    stock_code = st.text_input("Stock Code")
                    desc = st.text_input("Description")
                    unit = st.text_input("Unit")
                    qty = st.number_input("Qty", min_value=0)
                    location = st.text_input("LOCATION")
                    confirm_add = st.radio("هل تريد إضافة المنتج وحفظه؟", ["نعم", "لا"])
                    submitted = st.form_submit_button("حفظ")
                    if submitted:
                        if confirm_add == "نعم":
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
                        else:
                            st.info("❎ تم إلغاء إضافة المنتج الجديد.")
                        # إنهاء العملية بعد إضافة المنتج الجديد أو إلغاء الإضافة
                        st.session_state["operation_in_progress"] = False
                        st.session_state["current_code"] = None


if __name__ == "__main__":
    main()
