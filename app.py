import streamlit as st
import pandas as pd
import requests
import random

st.set_page_config(
    page_title="Fitness Exercise & Plan Explorer",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .badge-target { background-color: #e3f2fd; color: #1565c0; }
    .badge-bodypart { background-color: #f3e5f5; color: #7b1fa2; }
    .badge-equipment { background-color: #e8f5e9; color: #2e7d32; }
    .workout-day-box {
        background-color: #f8f9fa;
        border-left: 5px solid #2e7d32;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 中英对照字典 -----------------
BODY_PARTS_CN = {
    "back": "背部", "cardio": "有氧心肺", "chest": "胸部",
    "lower arms": "小臂 / 前臂", "lower legs": "小腿", "neck": "颈部",
    "shoulders": "肩部", "upper arms": "大臂 / 上臂", "upper legs": "大腿",
    "waist": "腰腹核心"
}

TARGET_MUSCLES_CN = {
    "abductors": "髋外展肌群", "abs": "腹肌", "adductors": "髋内收肌群",
    "biceps": "肱二头肌", "calves": "小腿肌群", "cardiovascular system": "心血管系统",
    "delts": "三角肌", "forearms": "前臂肌群", "glutes": "臀大肌 / 臀部",
    "hamstrings": "腘绳肌 (大腿后侧)", "lats": "背阔肌", "levator scapulae": "肩胛提肌",
    "pectorals": "胸大肌", "quads": "股四头肌 (大腿前侧)", "serratus anterior": "前锯肌",
    "spine": "脊柱肌群", "traps": "斜方肌", "triceps": "肱三头肌", "upper back": "上背部"
}

EQUIPMENT_CN = {
    "assisted": "辅助器械", "band": "弹力带", "barbell": "杠铃",
    "body weight": "徒手 / 自重", "bosu ball": "BOSU 半圆平衡球", "cable": "龙门架 / 绳索",
    "dumbbell": "哑铃", "elliptical machine": "椭圆机", "ez barbell": "EZ 曲柄杠铃",
    "hammer": "铁锤 / 训练锤", "kettlebell": "壶铃", "leverage machine": "杠杆器械",
    "medicine ball": "药球", "olympic barbell": "奥林匹克杠铃", "resistance band": "阻力带",
    "roller": "泡沫轴 / 滚轮", "rope": "战绳 / 跳绳", "skierg machine": "滑雪机",
    "sled machine": "负重雪橇", "smith machine": "史密斯机", "stability ball": "瑞士球 / 健身球",
    "stationary bike": "动感单车", "stepmill machine": "楼梯机", "tire": "重型轮胎",
    "trap bar": "六角杠铃", "upper body ergometer": "手摇车", "weighted": "负重加重",
    "wheel roller": "健腹轮"
}

def fmt_bodypart(val):
    return f"{BODY_PARTS_CN.get(str(val).lower(), '')} ({val})" if str(val).lower() in BODY_PARTS_CN else str(val).title()

def fmt_target(val):
    return f"{TARGET_MUSCLES_CN.get(str(val).lower(), '')} ({val})" if str(val).lower() in TARGET_MUSCLES_CN else str(val).title()

def fmt_equipment(val):
    return f"{EQUIPMENT_CN.get(str(val).lower(), '')} ({val})" if str(val).lower() in EQUIPMENT_CN else str(val).title()

# ----------------- 数据加载与标准化 -----------------
DATASET_RAW_URL = "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/master/data/exercises.json"
REPO_RAW_BASE = "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/master"

@st.cache_data(ttl=3600)
def load_exercise_data():
    resp = requests.get(DATASET_RAW_URL, timeout=15)
    resp.raise_for_status()
    raw_df = pd.DataFrame(resp.json())
    
    # 统一字段
    if 'bodyPart' in raw_df.columns and 'body_part' not in raw_df.columns:
        raw_df['body_part'] = raw_df['bodyPart']
    if 'secondaryMuscles' in raw_df.columns and 'secondary_muscles' not in raw_df.columns:
        raw_df['secondary_muscles'] = raw_df['secondaryMuscles']
        
    for col in ['equipment', 'body_part', 'target', 'name']:
        if col in raw_df.columns:
            raw_df[col] = raw_df[col].astype(str).str.strip().str.lower()
            
    return raw_df

try:
    with st.spinner("正在加载运动数据库..."):
        df = load_exercise_data()
except Exception as e:
    st.error(f"加载数据集失败: {e}")
    st.stop()

# 动作卡片渲染
def render_exercise_card(row, col):
    with col:
        st.subheader(str(row.get('name', '')).title())
        media_path = row.get('gif_url') or row.get('gifUrl') or row.get('image') or ''
        if media_path:
            media_url = media_path if str(media_path).startswith("http") else f"{REPO_RAW_BASE}/{str(media_path).lstrip('/')}"
            st.image(media_url, use_container_width=True)
        else:
            st.info("暂无动图")
            
        st.markdown(f"""
        <div>
            <span class="badge badge-target">🎯 {fmt_target(row.get('target', ''))}</span>
            <span class="badge badge-bodypart">🧍 {fmt_bodypart(row.get('body_part', ''))}</span>
            <span class="badge badge-equipment">⚙️ {fmt_equipment(row.get('equipment', ''))}</span>
        </div>
        """, unsafe_allow_html=True)
        
        instructions = row.get('instructions')
        if isinstance(instructions, list) and len(instructions) > 0:
            with st.expander("📖 动作要领"):
                for step_i, step_text in enumerate(instructions, 1):
                    st.markdown(f"**{step_i}.** {step_text}")
        st.markdown("<br>", unsafe_allow_html=True)

# ----------------- 页面主体 -----------------
st.title("🏋️‍♂️ 智能健身工坊：动作库与课表生成器")

tab_explore, tab_custom_plan, tab_weekly_plan = st.tabs([
    "🔍 动作检索库", 
    "⚡ 单日定制课表生成", 
    "📅 自动生成一周均衡课表"
])

# 获取纯净的器械列表供所有 tab 使用
all_equipments = sorted([e for e in df['equipment'].dropna().unique() if e])

# ==============================================================================
# TAB 1: 动作检索库 (原本正常的逻辑保留)
# ==============================================================================
with tab_explore:
    st.sidebar.header("🔍 动作库筛选")
    search_query = st.sidebar.text_input("动作名称关键词", placeholder="如: squat, bench, curl...")

    all_targets = sorted([t for t in df['target'].dropna().unique() if t])
    selected_targets = st.sidebar.multiselect("🎯 目标肌群", options=all_targets, format_func=fmt_target)

    all_bodyparts = sorted([b for b in df['body_part'].dropna().unique() if b])
    selected_bodyparts = st.sidebar.multiselect("🧍 身体部位", options=all_bodyparts, format_func=fmt_bodypart)

    selected_equipments = st.sidebar.multiselect("⚙️ 训练器械", options=all_equipments, format_func=fmt_equipment)

    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['name'].str.contains(search_query.strip(), case=False, na=False)]
    if selected_targets:
        filtered_df = filtered_df[filtered_df['target'].isin(selected_targets)]
    if selected_bodyparts:
        filtered_df = filtered_df[filtered_df['body_part'].isin(selected_bodyparts)]
    if selected_equipments:
        filtered_df = filtered_df[filtered_df['equipment'].isin(selected_equipments)]

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("筛选动作数", len(filtered_df))
    with col2: st.metric("涵盖肌群", filtered_df['target'].nunique())
    with col3: st.metric("身体部位", filtered_df['body_part'].nunique())
    with col4: st.metric("器械种类", filtered_df['equipment'].nunique())
    st.divider()

    if filtered_df.empty:
        st.info("未找到符合条件的动作。")
    else:
        PAGE_SIZE = 9
        total_pages = max(1, (len(filtered_df) - 1) // PAGE_SIZE + 1)
        p1, p2 = st.columns([1, 4])
        with p1: page_number = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1, key="explore_page")
        with p2: st.write(f"共 **{len(filtered_df)}** 个动作 | 第 **{page_number}** / **{total_pages}** 页")

        start_idx = (page_number - 1) * PAGE_SIZE
        page_data = filtered_df.iloc[start_idx:start_idx + PAGE_SIZE]
        
        cols_per_row = 3
        for r_i in range(0, len(page_data), cols_per_row):
            row_slice = page_data.iloc[r_i:r_i + cols_per_row]
            grid_cols = st.columns(cols_per_row)
            for c_idx, (_, row) in enumerate(row_slice.iterrows()):
                render_exercise_card(row, grid_cols[c_idx])


# ==============================================================================
# TAB 2: 单日定制课表生成 (纯净硬过滤)
# ==============================================================================
with tab_custom_plan:
    st.subheader("⚡ 单日个性化训练课表生成器")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        split_type = st.selectbox(
            "1. 选择主要训练部位 / 循环训练",
            options=[
                "胸部 (Chest)",
                "背部 (Back)",
                "腿部 (Legs)",
                "全身循环训练 (Full Body Circuit)"
            ]
        )
        action_count = st.slider("2. 动作数量 (个)", min_value=3, max_value=8, value=4)
        
    with col_t2:
        selected_plan_equipments = st.multiselect(
            "3. 必须使用的器械 (单选或多选)",
            options=all_equipments,
            format_func=fmt_equipment,
            default=["body weight"]  # 默认即为徒手/自重
        )

    # 部位映射表
    part_mapping = {
        "胸部 (Chest)": ["chest"],
        "背部 (Back)": ["back"],
        "腿部 (Legs)": ["upper legs", "lower legs"],
        "全身循环训练 (Full Body Circuit)": []
    }

    if st.button("🎲 立即生成训练课表", type="primary"):
        # 步骤 1：先严格按器械筛选（若选了徒手，绝对只有 body weight）
        if selected_plan_equipments:
            step1_df = df[df['equipment'].isin(selected_plan_equipments)].copy()
        else:
            step1_df = df.copy()

        # 步骤 2：在器械过滤后的池子里，再按身体部位筛选
        target_parts = part_mapping[split_type]
        if target_parts:
            final_pool = step1_df[step1_df['body_part'].isin(target_parts)].copy()
        else:
            final_pool = step1_df.copy()

        if final_pool.empty:
            st.error("⚠️ 该器械下没有找到对应部位的动作，请调整器械选项。")
        else:
            sample_size = min(action_count, len(final_pool))
            sampled_df = final_pool.sample(n=sample_size, random_state=random.randint(1, 9999))
            
            st.success(f"🎉 成功生成！已为您严格筛选出 **{sample_size}** 个纯符合器械条件的动作：")
            
            cols_per_row = 3
            for r_i in range(0, len(sampled_df), cols_per_row):
                row_slice = sampled_df.iloc[r_i:r_i + cols_per_row]
                grid_cols = st.columns(cols_per_row)
                for c_idx, (_, row) in enumerate(row_slice.iterrows()):
                    render_exercise_card(row, grid_cols[c_idx])


# ==============================================================================
# TAB 3: 自动生成一周均衡课表 (纯净硬过滤)
# ==============================================================================
with tab_weekly_plan:
    st.subheader("📅 自动生成一周均衡课表 (兼顾胸、背、腿、全身)")
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        actions_per_day = st.slider("1. 每日动作数量", min_value=3, max_value=6, value=4)
    with col_w2:
        weekly_equipments = st.multiselect(
            "2. 训练器械选择 (单选或多选)",
            options=all_equipments,
            format_func=fmt_equipment,
            default=["body weight"],  # 默认徒手
            key="weekly_equip_input"
        )
    
    # 均衡的经典周计划划分
    routine_template = [
        ("Day 1: 胸部专项 (Chest Day)", ["chest"]),
        ("Day 2: 背部专项 (Back Day)", ["back"]),
        ("Day 3: 休息日 (Rest Day)", None),
        ("Day 4: 腿部专项 (Leg Day)", ["upper legs", "lower legs"]),
        ("Day 5: 核心与全身循环 (Core & Full Body)", ["waist", "cardio", "chest", "back", "upper legs"]),
        ("Day 6: 休息日 (Rest Day)", None),
        ("Day 7: 休息日 (Rest Day)", None)
    ]

    if st.button("🚀 生成整周课表", type="primary"):
        # 步骤 1：先全局按器械硬切片
        if weekly_equipments:
            base_equipment_pool = df[df['equipment'].isin(weekly_equipments)].copy()
        else:
            base_equipment_pool = df.copy()

        markdown_export = "# 🏋️‍♂️ 一周均衡健身课表\n\n"
        
        for day_title, day_parts in routine_template:
            st.markdown(f"<div class='workout-day-box'><h4>📌 {day_title}</h4></div>", unsafe_allow_html=True)
            markdown_export += f"## {day_title}\n"
            
            # 休息日直接跳过抽样
            if day_parts is None:
                st.write("💤 安排休息与机能恢复。")
                markdown_export += "- 充分休息与拉伸放松\n\n"
                st.divider()
                continue
            
            # 步骤 2：在器械库中严格筛选对应的 body_part
            day_pool = base_equipment_pool[base_equipment_pool['body_part'].isin(day_parts)]
            
            if day_pool.empty:
                st.warning(f"在选定器械中未找到对应部位的动作。")
            else:
                sample_count = min(actions_per_day, len(day_pool))
                day_sampled = day_pool.sample(n=sample_count, random_state=random.randint(1, 9999))
                
                d_cols = st.columns(sample_count)
                for idx, (_, row) in enumerate(day_sampled.iterrows()):
                    with d_cols[idx]:
                        st.markdown(f"**{idx+1}. {str(row['name']).title()}**")
                        st.caption(f"{fmt_bodypart(row.get('body_part',''))} | {fmt_equipment(row.get('equipment',''))}")
                        media_path = row.get('gif_url') or row.get('gifUrl') or row.get('image') or ''
                        if media_path:
                            media_url = media_path if str(media_path).startswith("http") else f"{REPO_RAW_BASE}/{str(media_path).lstrip('/')}"
                            st.image(media_url, use_container_width=True)
                            
                    markdown_export += f"- {str(row['name']).title()} ({fmt_bodypart(row.get('body_part',''))} / {fmt_equipment(row.get('equipment',''))})\n"
            
            markdown_export += "\n"
            st.divider()

        st.download_button(
            label="📥 下载整周课表 (Markdown 文本)",
            data=markdown_export,
            file_name="weekly_routine.md",
            mime="text/markdown"
        )
