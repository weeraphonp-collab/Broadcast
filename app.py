import streamlit as st
import pandas as pd
import os
import datetime
import uuid
import altair as alt
import json

# --- 1. การตั้งค่าธีมและสไตล์ (Official Red & Dark) ---
def apply_enterprise_style():
    st.markdown("""
        <style>
        .stButton>button {
            background-color: #E3242B;
            color: white;
            border-radius: 5px;
            border: none;
        }
        .stButton>button:hover {
            background-color: #B21C22;
            color: white;
        }
        div[data-testid="stMetricValue"] {
            color: #E3242B;
        }
        .stProgress > div > div > div > div {
            background-color: #E3242B;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px;
            border-color: #333333 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #1E1E1E;
            border-radius: 5px 5px 0px 0px;
            padding: 10px 20px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #E3242B !important;
            color: white !important;
        }
        .streamlit-expanderHeader {
            background-color: #1E1E1E !important;
            border-radius: 5px;
        }
        /* ปรับแต่งปุ่มลบให้ดูคลีน มินิมอล */
        .small-icon-btn button {
            padding: 0px !important;
            font-size: 12px !important;
            width: 40px !important;
            height: 24px !important;
            min-height: 24px !important;
            background-color: transparent !important;
            border: 1px solid #444 !important;
            border-radius: 4px !important;
            color: #aaa !important;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .small-icon-btn button:hover {
            border-color: #E3242B !important;
            color: #E3242B !important;
            background-color: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)

# 🎯 ระบบฐานข้อมูล Local
DB_DIR = ".streamlit"
CAMPAIGN_DB = os.path.join(DB_DIR, "campaign_history.json")

def setup_config():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    if not os.path.exists(CAMPAIGN_DB):
        with open(CAMPAIGN_DB, "w") as f: json.dump([], f)

def load_db(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                if 'date' in item and isinstance(item['date'], str):
                    item['date'] = datetime.datetime.strptime(item['date'], '%Y-%m-%d').date()
            return data
    except:
        return []

def save_db(data, filepath):
    serializable_data = []
    for item in data:
        new_item = item.copy()
        if isinstance(new_item.get('date'), datetime.date):
            new_item['date'] = new_item['date'].strftime('%Y-%m-%d')
        serializable_data.append(new_item)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=4)

setup_config()
st.set_page_config(page_title="Broadcast Analyzer", layout="wide")
apply_enterprise_style()

campaign_history = load_db(CAMPAIGN_DB)

if 'toast_msg' in st.session_state:
    st.toast(st.session_state['toast_msg']['msg']) 
    del st.session_state['toast_msg']

# --- Helper Function อ่านไฟล์ ---
def read_and_clean_uid(file_path):
    try:
        df = pd.read_csv(file_path, header=None, names=['uid'], dtype=str)
        df['uid'] = df['uid'].astype(str).str.strip()
        df = df[df['uid'].notna() & (df['uid'] != '') & (df['uid'] != 'nan')]
        return df[['uid']].drop_duplicates()
    except Exception as e:
        st.warning(f"ข้ามไฟล์ {os.path.basename(file_path)} เนื่องจาก: {e}")
        return pd.DataFrame(columns=['uid'])

# --- 🎯 จัดการตัวแปรความจำสำหรับกระบะพักและระบบแก้ไข ---
if 'stage_inc' not in st.session_state: st.session_state['stage_inc'] = []
if 'stage_exc' not in st.session_state: st.session_state['stage_exc'] = []
if 'stage_selector' not in st.session_state: st.session_state['stage_selector'] = []
if 'edit_id' not in st.session_state: st.session_state['edit_id'] = None
if 'camp_date_input' not in st.session_state: st.session_state['camp_date_input'] = datetime.date.today()
if 'is_executed' not in st.session_state: st.session_state['is_executed'] = False # 🎯 ตัวจำสถานะปุ่ม Execute

def clear_staging():
    st.session_state['stage_inc'] = []
    st.session_state['stage_exc'] = []
    st.session_state['stage_selector'] = []
    st.session_state['edit_id'] = None 
    st.session_state['camp_date_input'] = datetime.date.today()

def load_campaign_to_edit(camp_id):
    for c in campaign_history:
        if c['id'] == camp_id:
            st.session_state['stage_inc'] = list(c['includes'])
            st.session_state['stage_exc'] = list(c['excludes'])
            st.session_state['camp_date_input'] = c['date']
            st.session_state['edit_id'] = c['id']
            st.session_state['toast_msg'] = {'msg': "โหลดข้อมูลลงกระบะเพื่อแก้ไขแล้ว"}
            break

def process_staging(stage_type):
    selected = st.session_state.get('stage_selector', [])
    if selected:
        if stage_type == 'inc':
            st.session_state['stage_inc'] = list(set(st.session_state['stage_inc'] + selected))
            st.session_state['toast_msg'] = {'msg': "เพิ่มลง Include เรียบร้อย"}
        elif stage_type == 'exc':
            st.session_state['stage_exc'] = list(set(st.session_state['stage_exc'] + selected))
            st.session_state['toast_msg'] = {'msg': "เพิ่มลง Exclude เรียบร้อย"}
        st.session_state['stage_selector'] = []

def submit_broadcast_callback():
    c_date = st.session_state['camp_date_input']
    if not st.session_state['stage_inc']:
        st.session_state['add_error'] = True
    else:
        edit_id = st.session_state.get('edit_id')
        if edit_id: 
            for c in campaign_history:
                if c['id'] == edit_id:
                    c['date'] = c_date
                    c['includes'] = list(st.session_state['stage_inc'])
                    c['excludes'] = list(st.session_state['stage_exc'])
                    break
            st.session_state['toast_msg'] = {'msg': "อัปเดตข้อมูล Broadcast เรียบร้อย"}
        else: 
            new_camp = {
                'id': str(uuid.uuid4()), 
                'date': c_date,
                'includes': list(st.session_state['stage_inc']),
                'excludes': list(st.session_state['stage_exc']),
                'weight': 1
            }
            campaign_history.append(new_camp)
            st.session_state['toast_msg'] = {'msg': "บันทึกประวัติ Broadcast เรียบร้อย"}
            
        save_db(campaign_history, CAMPAIGN_DB) 
        st.session_state['is_executed'] = False # 🎯 เซฟใหม่ปุ๊บ ล้างหน้า Dashboard เก่าทิ้งก่อน
        clear_staging()

def delete_campaign(camp_id):
    global campaign_history
    campaign_history = [c for c in campaign_history if c['id'] != camp_id]
    save_db(campaign_history, CAMPAIGN_DB)
    st.session_state['is_executed'] = False # 🎯 ลบข้อมูลก็ต้องล้างหน้า Dashboard ทิ้งเหมือนกัน
    st.session_state['toast_msg'] = {'msg': "ลบ Broadcast เรียบร้อย"}

# --- 2. ส่วนหัวโปรแกรม ---
st.title("UID Broadcast Count")
st.caption("")
st.divider()

with st.container(border=True):
    folder_path = st.text_input("ระบุตำแหน่งไดเรกทอรี (Directory Path):", value='/Users/weeraphonphetluecha/รวม uid งวด 01032026')

if os.path.isdir(folder_path):
    allowed_extensions = ('.csv', '.txt')
    target_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(allowed_extensions) and file != 'summary_broadcast_report.csv':
                target_files.append(os.path.relpath(os.path.join(root, file), folder_path))
    target_files.sort()
    
    if target_files:
        st.write("")
        
        # ==========================================================
        # 🎯 โซนที่ 1: เตรียมแคมเปญ (Staging Area)
        # ==========================================================
        with st.container(border=True):
            st.subheader("1. Select Broadcast File")
            
            camp_date = st.date_input("วันที่ส่ง Broadcast:", key='camp_date_input')
            st.markdown("---")
            
            search_keyword = st.text_input("พิมพ์ค้นหารายชื่อไฟล์:", placeholder="ค้นหา...")
            display_options = [f for f in target_files if search_keyword.lower() in f.lower()] if search_keyword.strip() else target_files
            
            selected_to_stage = st.multiselect(
                "คลิกเพื่อเลือกไฟล์:", 
                options=display_options,
                key='stage_selector',
                placeholder="เลือกไฟล์ที่ต้องการ..."
            )
            
            col_add_inc, col_add_exc = st.columns(2)
            with col_add_inc: st.button("Include", use_container_width=True, on_click=process_staging, args=('inc',))
            with col_add_exc: st.button("Exclude", use_container_width=True, on_click=process_staging, args=('exc',))

            st.markdown("<br><h5>Waiting for Process</h5>", unsafe_allow_html=True)
            col_clear_draft, col_submit_draft = st.columns([1, 2])
            with col_clear_draft: st.button("Clear", use_container_width=True, on_click=clear_staging)
            with col_submit_draft:
                btn_label = "อัปเดตข้อมูล Broadcast" if st.session_state.get('edit_id') else "ยืนยันบันทึก Broadcast"
                st.button(btn_label, type="primary", use_container_width=True, on_click=submit_broadcast_callback)
                if st.session_state.get('add_error'):
                    st.error("ต้องมีไฟล์เป้าหมาย (Include) อย่างน้อย 1 รายการ")
                    st.session_state['add_error'] = False

            st.write("")
            draft_col1, draft_col2 = st.columns(2)
            
            with draft_col1:
                with st.container(border=True):
                    st.markdown("<div style='color: #4CAF50; font-weight: bold; font-size: 16px; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px;'>Include:</div>", unsafe_allow_html=True)
                    with st.container(height=250, border=False): 
                        if not st.session_state['stage_inc']:
                            st.caption("ว่างเปล่า...")
                        for f in st.session_state['stage_inc']:
                            c_name, c_del = st.columns([8.5, 1.5])
                            c_name.markdown(f"<span style='font-size: 13px;'>{f}</span>", unsafe_allow_html=True)
                            with c_del:
                                st.markdown("<div class='small-icon-btn'>", unsafe_allow_html=True)
                                if st.button("ลบ", key=f"del_inc_{f}"):
                                    st.session_state['stage_inc'].remove(f)
                                    st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
            
            with draft_col2:
                with st.container(border=True):
                    st.markdown("<div style='color: #E3242B; font-weight: bold; font-size: 16px; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px;'>Exclude:</div>", unsafe_allow_html=True)
                    with st.container(height=250, border=False): 
                        if not st.session_state['stage_exc']:
                            st.caption("ว่างเปล่า...")
                        for f in st.session_state['stage_exc']:
                            c_name, c_del = st.columns([8.5, 1.5])
                            c_name.markdown(f"<span style='font-size: 13px;'>{f}</span>", unsafe_allow_html=True)
                            with c_del:
                                st.markdown("<div class='small-icon-btn'>", unsafe_allow_html=True)
                                if st.button("ลบ", key=f"del_exc_{f}"):
                                    st.session_state['stage_exc'].remove(f)
                                    st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
        
        st.write("")
        
        # ==========================================================
        # 🎯 โซนที่ 2: ประวัติและการกรองวันที่
        # ==========================================================
        with st.container(border=True):
            st.subheader("Broadcast Processing")
            
            if campaign_history:
                # 🎯 ตั้ง Default ให้เป็นวันที่ปัจจุบัน (today) เสมอ
                today = datetime.date.today()
                
                date_range = st.date_input(
                    "เลือกช่วงวันที่ที่ต้องการคำนวณ:", 
                    value=(today, today), 
                    on_change=lambda: st.session_state.update({'is_executed': False}) # 🎯 ถ้าเปลี่ยนวัน ให้เคลียร์หน้า Dashboard ทิ้ง
                )
                
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                elif isinstance(date_range, tuple) and len(date_range) == 1:
                    start_date = end_date = date_range[0]
                else:
                    start_date = end_date = date_range

                filtered_basket = [c for c in campaign_history if start_date <= c['date'] <= end_date]
                
                st.markdown(f"**รายการที่พบในช่วงเวลาที่เลือก: {len(filtered_basket)} Broadcast**")
                st.write("")
                
                if filtered_basket:
                    unique_dates = sorted(list(set([c['date'] for c in filtered_basket])))
                    
                    for d in unique_dates:
                        daily_camps = [c for c in filtered_basket if c['date'] == d]
                        
                        with st.expander(f"วันที่ {d.strftime('%d/%m/%Y')} (จำนวน {len(daily_camps)} Broadcast)"):
                            for i, item in enumerate(daily_camps):
                                c1, c2, c3 = st.columns([8, 1, 1]) 
                                
                                with c1: 
                                    st.markdown(f"**Broadcast {i+1}**")
                                    st.markdown(f"<span style='color: #4CAF50; font-size: 13px; font-weight: bold;'>Include:</span> <span style='font-size: 13px;'>{', '.join(item['includes'])}</span>", unsafe_allow_html=True)
                                    if item['excludes']: 
                                        st.markdown(f"<span style='color: #E3242B; font-size: 13px; font-weight: bold;'>Exclude:</span> <span style='font-size: 13px;'>{', '.join(item['excludes'])}</span>", unsafe_allow_html=True)
                                
                                with c2:
                                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                                    st.button("แก้ไข", key=f"edit_basket_{item['id']}", use_container_width=True, on_click=load_campaign_to_edit, args=(item['id'],))

                                with c3:
                                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                                    if st.button("ลบ", key=f"del_basket_{item['id']}", use_container_width=True):
                                        delete_campaign(item['id'])
                                        st.rerun()
                                        
                                st.markdown("<hr style='margin: 8px 0px; border-color: #eee;'>", unsafe_allow_html=True)
                
                st.write("")
                col_clear_db, col_process = st.columns([1, 2])
                with col_clear_db:
                    if st.button("ล้างประวัติทั้งหมด"):
                        save_db([], CAMPAIGN_DB)
                        st.session_state['is_executed'] = False # 🎯 ล้างด้วย
                        st.rerun()
                
                with col_process:
                    # 🎯 ผูกฟังก์ชันจำสถานะตอนกดปุ่ม
                    def run_execute():
                        st.session_state['is_executed'] = True
                    st.button(f"Execute Process ({len(filtered_basket)} Broadcast)", type="primary", use_container_width=True, on_click=run_execute)
            else:
                st.info("ยังไม่มีประวัติ Broadcast ที่บันทึกไว้")
                filtered_basket = []

        # ==========================================================
        # 🎯 โซนที่ 3: ลอจิกการประมวลผล Dashboard
        # ==========================================================
        # 🎯 เปลี่ยนจากการเช็คปุ่มกด เป็นการเช็คความจำในระบบ
        if filtered_basket and st.session_state.get('is_executed'):
            st.write("")
            with st.container(border=True):
                all_data = []
                broadcast_exports = [] 
                p_bar = st.progress(0)
                
                for i, item in enumerate(filtered_basket):
                    include_dfs = []
                    for inc_file in item['includes']:
                        inc_path = os.path.join(folder_path, inc_file)
                        include_dfs.append(read_and_clean_uid(inc_path))
                    
                    if not include_dfs: continue
                    df_campaign = pd.concat(include_dfs, ignore_index=True).drop_duplicates()
                    
                    if item['excludes']:
                        exclude_dfs = []
                        for exc_file in item['excludes']:
                            exc_path = os.path.join(folder_path, exc_file)
                            exclude_dfs.append(read_and_clean_uid(exc_path))
                        if exclude_dfs:
                            df_exclude = pd.concat(exclude_dfs, ignore_index=True).drop_duplicates()
                            df_campaign = df_campaign[~df_campaign['uid'].isin(df_exclude['uid'])]
                    
                    if not df_campaign.empty:
                        df_campaign['w'] = item['weight']
                        df_campaign['date'] = item['date']
                        all_data.append(df_campaign)
                        
                        csv_data = df_campaign[['uid']].to_csv(index=False, header=False).encode('utf-8-sig')
                        broadcast_exports.append({
                            'name': f"Broadcast {i+1} (ของวันที่ {item['date'].strftime('%d/%m/%Y')})",
                            'count': len(df_campaign),
                            'csv': csv_data,
                            'id': item['id'],
                            'filename': f"Broadcast_{i+1}_{item['date'].strftime('%Y%m%d')}.csv"
                        })
                    
                    p_bar.progress((i + 1) / len(filtered_basket))
                
                if all_data:
                    res = pd.concat(all_data, ignore_index=True)
                    final_total = res.groupby('uid')['w'].sum().reset_index()
                    final_total.columns = ['UID', 'Frequency']
                    daily_summary = res.groupby(['date', 'uid'])['w'].sum().reset_index()
                    
                    st.success("ประมวลผลเสร็จสิ้น")
                    st.markdown("<h3 style='text-align: center;'>Analysis Summary Dashboard</h3>", unsafe_allow_html=True)
                    
                    with st.container(border=True):
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("ลูกค้ารวม (Unique)", f"{len(final_total):,}")
                        m2.metric("จำนวน Broadcast", f"{len(filtered_basket)}")
                        m3.metric("ความถี่เฉลี่ย", f"{final_total['Frequency'].mean():.2f}")
                        m4.metric("ความถี่สูงสุด", f"{final_total['Frequency'].max()}")
                    
                    st.write("")
                    
                    tab_total, tab_daily, tab_indv = st.tabs(["Total Summary", "Daily Summary", "Individual Broadcast"])
                    
                    with tab_total:
                        summary = final_total['Frequency'].value_counts().reset_index()
                        summary.columns = ['Count', 'Users']
                        summary = summary.sort_values(by='Count')
                        
                        st.markdown("<h5 style='text-align: center; margin-bottom: 20px;'>สัดส่วนความถี่ในการได้รับข้อความ</h5>", unsafe_allow_html=True)
                        base_chart = alt.Chart(summary).encode(
                            x=alt.X('Count:O', title='จำนวนครั้ง (Count)', axis=alt.Axis(labelAngle=0)),
                            y=alt.Y('Users:Q', title='จำนวนลูกค้า (Users)')
                        )
                        st.altair_chart(base_chart.mark_bar(color="#E3242B") + base_chart.mark_text(align='center', baseline='bottom', dy=-5, fontSize=14, fontWeight='bold').encode(text=alt.Text('Users:Q', format=',')), use_container_width=True)
                        
                        st.divider()
                        th1, th2, th3 = st.columns([1.5, 2, 2.5])
                        with th1: st.markdown("<div style='text-align: center; font-weight: bold;'>Count</div>", unsafe_allow_html=True)
                        with th2: st.markdown("<div style='text-align: center; font-weight: bold;'>Users</div>", unsafe_allow_html=True)
                        with th3: st.markdown("<div style='text-align: center; font-weight: bold;'>Export</div>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 10px 0px; border-color: #555;'>", unsafe_allow_html=True)
                        
                        for index, row in summary.sort_values(by='Count').iterrows():
                            val, users = row['Count'], row['Users']
                            export_df = final_total[final_total['Frequency'] == val][['UID']]
                            csv = export_df.to_csv(index=False, header=False).encode('utf-8-sig')
                            tr1, tr2, tr3 = st.columns([1.5, 2, 2.5])
                            with tr1: st.markdown(f"<div style='text-align: center; padding-top: 8px;'>{val}</div>", unsafe_allow_html=True)
                            with tr2: st.markdown(f"<div style='text-align: center; padding-top: 8px;'>{users:,}</div>", unsafe_allow_html=True)
                            with tr3:
                                st.download_button(label=f"โหลดกลุ่ม {val} ครั้ง", data=csv, file_name=f"Total_Group_{val}.csv", mime="text/csv", key=f"dl_tot_{val}", use_container_width=True)
                            st.markdown("<hr style='margin: 5px 0px; border-color: #222;'>", unsafe_allow_html=True)
                    
                    with tab_daily:
                        st.markdown("<h5 style='text-align: center; margin-bottom: 20px;'>ตารางสรุปจำนวนลูกค้าแยกตามวันที่และความถี่</h5>", unsafe_allow_html=True)
                        pivot_df = daily_summary.pivot_table(index='date', columns='w', values='uid', aggfunc='count', fill_value=0)
                        pivot_df.index = [d.strftime('%d/%m/%Y') for d in pivot_df.index]
                        pivot_df.columns = [f"บอร์ด {col} ครั้ง" for col in pivot_df.columns]
                        pivot_df['Total'] = pivot_df.sum(axis=1)
                        for col in pivot_df.columns: pivot_df[col] = pivot_df[col].apply(lambda x: f"{int(x):,}" if x > 0 else "")
                        st.dataframe(pivot_df.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
                        
                        st.divider()
                        st.markdown("**Download Daily Data**")
                        for d in sorted(daily_summary['date'].unique()):
                            date_str = d.strftime('%d/%m/%Y')
                            day_data = daily_summary[daily_summary['date'] == d]
                            with st.expander(f"Data: {date_str}"):
                                cols = st.columns(4)
                                for idx, f_val in enumerate(sorted(day_data['w'].unique(), reverse=True)):
                                    df_dl = day_data[day_data['w'] == f_val][['uid']]
                                    csv_dl = df_dl.to_csv(index=False, header=False).encode('utf-8-sig')
                                    with cols[idx % 4]:
                                        st.download_button(label=f"กลุ่ม {f_val} ครั้ง", data=csv_dl, file_name=f"Daily_{date_str}_F{f_val}.csv", mime="text/csv", key=f"dl_day_{d}_{f_val}", use_container_width=True)
                    
                    with tab_indv:
                        st.markdown("<h5 style='text-align: center; margin-bottom: 20px;'>ดาวน์โหลด UID แยกราย Broadcast (หัก Exclude แล้ว)</h5>", unsafe_allow_html=True)
                        
                        th1, th2, th3 = st.columns([2, 1, 1.5])
                        with th1: st.markdown("<div style='font-weight: bold;'>Broadcast Detail</div>", unsafe_allow_html=True)
                        with th2: st.markdown("<div style='text-align: center; font-weight: bold;'>Net Users</div>", unsafe_allow_html=True)
                        with th3: st.markdown("<div style='text-align: center; font-weight: bold;'>Export</div>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 10px 0px; border-color: #555;'>", unsafe_allow_html=True)
                        
                        for b in broadcast_exports:
                            tr1, tr2, tr3 = st.columns([2, 1, 1.5])
                            with tr1: st.markdown(f"<div style='padding-top: 8px;'><b>{b['name']}</b></div>", unsafe_allow_html=True)
                            with tr2: st.markdown(f"<div style='text-align: center; padding-top: 8px;'>{b['count']:,}</div>", unsafe_allow_html=True)
                            with tr3:
                                st.download_button(label="📥 โหลดไฟล์", data=b['csv'], file_name=b['filename'], mime="text/csv", key=f"dl_indv_{b['id']}", use_container_width=True)
                            st.markdown("<hr style='margin: 5px 0px; border-color: #222;'>", unsafe_allow_html=True)
                else:
                    st.warning("ไม่พบข้อมูล UID")
                                
    else:
        st.warning("ไม่พบไฟล์ที่รองรับในไดเรกทอรีนี้")
else:
    st.error("ไม่พบตำแหน่งโฟลเดอร์ที่ระบุ กรุณาตรวจสอบ Directory Path")