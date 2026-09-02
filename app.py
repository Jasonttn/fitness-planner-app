import streamlit as st
import pandas as pd
import requests
import random

st.set_page_config(
    page_title="Fitness Plan & Exercise Explorer",
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
    "back": "背部",
    "cardio": "有氧心肺",
    "chest": "胸部",
    "lower arms": "小臂 / 前臂",
    "lower legs": "小腿",
    "neck": "颈部",
    "shoulders": "肩部",
    "upper arms": "大臂 / 上臂",
    "upper legs": "大腿",
    "waist": "腰腹核心"
}

TARGET_MUSCLES_CN = {
    "abductors": "髋外展肌群",
    "abs": "腹肌",
    "adductors": "髋内收肌群",
    "biceps": "肱二头肌",
    "calves": "小腿肌群",
    "cardiovascular system": "心血管系统",
    "delts": "三角肌",
    "forearms": "前臂肌群",
    "glutes": "臀大肌 / 臀部",
    "hamstrings": "腘绳肌 (大腿后侧)",
    "lats": "背阔肌",
    "levator scapulae": "肩胛提肌",
    "pectorals": "胸大肌",
    "quads": "股四头肌 (大腿前侧)",
    "serratus anterior": "前锯肌",
    "spine": "脊柱肌群",
    "traps": "斜方肌",
    "triceps": "肱三头肌",
    "upper back": "上背部"
}

EQUIPMENT_CN = {
    "assisted": "辅助器械",
    "band": "弹力带",
    "barbell": "杠铃",
    "body weight": "徒手 / 自重",
    "bosu ball": "BOSU 半圆平衡球",
    "cable": "龙门架 / 绳索",
    "dumbbell": "哑铃",
    "elliptical machine": "椭圆机",
    "ez barbell": "EZ 曲柄杠铃",
    "hammer": "铁锤 / 训练锤",
    "kettlebell": "壶铃",
    "leverage machine": "杠杆器械",
    "medicine ball": "药球",
    "olympic barbell": "奥林匹克杠铃",
    "resistance band": "阻力带",
    "roller": "泡沫轴 / 滚轮",
    "rope": "战绳 / 跳绳",
    "skierg machine": "滑雪机",
    "sled machine": "负重雪橇",
    "smith machine": "史密斯机",
    "stability ball": "瑞士球 / 健身球",
    "stationary bike": "动感单车",
    "stepmill machine": "楼梯机",
    "tire": "重型轮胎",
    "trap bar": "六角杠铃 (Trap Bar)",
    "upper body ergometer": "上半身手摇车",
    "weighted": "负重加重",
    "wheel roller": "健腹轮"
}

def fmt_bodypart(val):
    cn = BODY_PARTS_CN.get(str(val).strip().lower(), "")
    return f"{cn} ({val})" if cn else str(val).title()

def fmt_target(val):
    cn = TARGET_MUSCLES_CN.get(str(val).strip().lower(), "")
    return f"{cn} ({val})" if cn else str(val).title()

def fmt_equipment(val):
    cn = EQUIPMENT_CN.get(str(val).strip().lower(), "")
    return f"{cn} ({val})" if cn else str(val).title()

# ----------------- 数据加载与严格清洗 -----------------
DATASET_RAW_URL = "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/master/data/exercises.json"
REPO_RAW_BASE = "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/master"

@st.cache_data(ttl=3600)
def load_exercise_data():
    resp = requests.get(DATASET_RAW_URL, timeout=15)
    resp.raise_for_status()
    raw_df = pd.DataFrame(resp.json())
    
    # 统一字段名
    if 'bodyPart' in raw_df.columns and 'body_part' not in raw_df.columns:
        raw_df['body_part'] = raw_df['bodyPart']
    if 'secondaryMuscles' in raw_df.columns and 'secondary_muscles' not in raw_df.columns:
        raw_df['secondary_muscles'] = raw_df['secondaryMuscles']
    
    # 关键清洗：统一小写并剔除首尾不可见字符
    for col in ['equipment', 'body_part', 'target']:
        if col in raw_df.columns:
            raw_df[col] = raw_df[col].astype(str).str.strip().str.lower()
            
    return raw_df

try:
    with st.spinner("正在初始化运动数据库..."):
        df = load_exercise_data()
except Exception as e:
    st.error(f"加载数据集失败: {e}")
    st.stop()

# ----------------- 页面顶层导航 -----------------
st.title("🏋️‍♂️ 智能健身工坊：动作库与课表生成器")

tab_explore, tab_custom_plan, tab_weekly_plan = st.tabs([
    "🔍 动作检索库", 
    "⚡ 单日定制课表生成", 
    "📅 自动生成一周均衡课表"
])

def render_exercise_card(row, col):
    with col:
        st.subheader(str(row.get('name', '')).title())
        media_path = row.get('gif_url') or row.get('gifUrl') or row.get('image') or ''
        if media_path:
            media_url = media_path if str(media_path).startswith("http") else f"{REPO_RAW_BASE}/{str(media_path).lstrip('/')}"
            st.image(media_url, use_container_width=True)
        else:
            st.info("暂无动图")
            
        target_label = fmt_target(row.get('target', ''))
        bodypart_label = fmt_bodypart(row.get('body_part', ''))
        equip_label = fmt_equipment(row.get('equipment', ''))
        
        st.markdown(f"""
        <div>
            <span class="badge badge-target">🎯 {target_label}</span>
            <span class="badge badge-bodypart">🧍 {bodypart_label}</span>
            <span class="badge badge-equipment">⚙️ {equip_label}</span>
        </div>
        """, unsafe_allow_html=True)
        
        sec_muscles = row.get('secondary_muscles') or row.get('secondaryMuscles')
        if isinstance(sec_muscles, list) and len(sec_muscles) > 0:
            sec_cn_list = [fmt_target(m) for m in sec_muscles]
            st.caption(f"**协同肌群:** {', '.join(sec_cn_list)}")
            
        instructions = row.get('instructions')
        if isinstance(instructions, list) and len(instructions) > 0:
            with st.expander("📖 动作要领"):
                for step_i, step_text in enumerate(instructions, 1):
                    st.markdown(f"**{step_i}.** {step_text}")
        elif isinstance(instructions, str) and instructions.strip():
            with st.expander("📖 动作要领"):
                st.write(instructions)
        st.markdown("<br>", unsafe_allow_html=True)


# ==============================================================================
# TAB 1: 动作检索库
# ==============================================================================
with tab_explore:
    st.sidebar.header("🔍 动作库筛选")
    search_query = st.sidebar.text_input("动作名称关键词", placeholder="如: squat, bench, push up...")

    all_targets = sorted([t for t in df['target'].dropna().unique() if t])
    selected_targets = st.sidebar.multiselect("🎯 目标肌群", options=all_targets, format_func=fmt_target)

    all_bodyparts = sorted([b for b in df['body_part'].dropna().unique() if b])
    selected_bodyparts = st.sidebar.multiselect("🧍 身体部位", options=all_bodyparts, format_func=fmt_bodypart)

    all_equipments = sorted([e for e in df['equipment'].dropna().unique() if e])
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
        st.info("未找到符合条件的动作，请调整筛选条件。")
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
# TAB 2: 单日定制课表生成
# ==============================================================================
with tab_custom_plan:
    st.subheader("⚡ 单日个性化训练课表生成器")
    st.caption("选择训练模式、部位、可用器械与动作数量，系统将严格按照器械限制从库中筛选。")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        split_type = st.selectbox(
            "1. 选择训练模式 / 分化类型",
            options=[
                "三分化 - 推 (Push: 胸/肩/肱三头)",
                "三分化 - 拉 (Pull: 背/肱二头/后束)",
                "三分化 - 腿 (Legs: 股四头/腘绳/臀/小腿)",
                "单一部位专注 - 胸部 (Chest)",
                "单一部位专注 - 背部 (Back)",
                "单一部位专注 - 腿部 (Legs)",
                "单一部位专注 - 肩部 (Shoulders)",
                "单一部位专注 - 手臂 (Arms)",
                "单一部位专注 - 核心 (Core/Waist)",
                "全身循环训练 (Full Body Circuit)"
            ]
        )
        action_count = st.slider("2. 挑选动作数量 (个)", min_value=3, max_value=10, value=5)
        
    with col_t2:
        avail_equipments = sorted([e for e in df['equipment'].dropna().unique() if e])
        selected_plan_equipments = st.multiselect(
            "3. 选择可用器械种类 (默认留空代表支持全部器械)",
            options=avail_equipments,
            format_func=fmt_equipment,
            default=[]
        )
        sets_reps_style = st.selectbox(
            "4. 推荐组数与每组次数 (Reps)",
            options=["肌肥大增肌 (4 组 x 8-12 次)", "力量主导 (5 组 x 5 次)", "肌耐力 / 减脂循环 (3 组 x 15-20 次)"]
        )

    split_mapping = {
        "三分化 - 推 (Push: 胸/肩/肱三头)": {"targets": ["pectorals", "delts", "triceps", "serratus anterior"], "body_parts": ["chest", "shoulders", "upper arms"]},
        "三分化 - 拉 (Pull: 背/肱二头/后束)": {"targets": ["lats", "upper back", "traps", "biceps", "forearms", "spine"], "body_parts": ["back", "upper arms", "lower arms"]},
        "三分化 - 腿 (Legs: 股四头/腘绳/臀/小腿)": {"targets": ["quads", "hamstrings", "glutes", "calves", "abductors", "adductors"], "body_parts": ["upper legs", "lower legs"]},
        "单一部位专注 - 胸部 (Chest)": {"targets": ["pectorals", "serratus anterior"], "body_parts": ["chest"]},
        "单一部位专注 - 背部 (Back)": {"targets": ["lats", "upper back", "traps", "spine"], "body_parts": ["back"]},
        "单一部位专注 - 腿部 (Legs)": {"targets": ["quads", "hamstrings", "glutes", "calves"], "body_parts": ["upper legs", "lower legs"]},
        "单一部位专注 - 肩部 (Shoulders)": {"targets": ["delts", "levator scapulae"], "body_parts": ["shoulders"]},
        "单一部位专注 - 手臂 (Arms)": {"targets": ["biceps", "triceps", "forearms"], "body_parts": ["upper arms", "lower arms"]},
        "单一部位专注 - 核心 (Core/Waist)": {"targets": ["abs", "spine"], "body_parts": ["waist"]},
        "全身循环训练 (Full Body Circuit)": {"targets": [], "body_parts": []}
    }

    if st.button("🎲 立即生成训练课表", type="primary"):
        # 1. 严格器械硬过滤
        if selected_plan_equipments:
            pool_df = df[df['equipment'].isin(selected_plan_equipments)].copy()
        else:
            pool_df = df.copy()
            
        # 2. 部位软匹配过滤
        condition = split_mapping[split_type]
        if condition["targets"] or condition["body_parts"]:
            match_mask = (pool_df['target'].isin(condition["targets"])) | (pool_df['body_part'].isin(condition["body_parts"]))
            pool_df = pool_df[match_mask]
            
        if pool_df.empty:
            st.error("⚠️ 在所选器械与部位条件下未找到匹配动作。若选择徒手，请确认该部位库中是否有纯自重动作，或增加其他可选器械。")
        else:
            sample_size = min(action_count, len(pool_df))
            sampled_df = pool_df.sample(n=sample_size, random_state=random.randint(1, 9999))
            
            st.success(f"🎉 成功生成专属训练课表！包含 **{sample_size}** 个精选动作（配置建议：{sets_reps_style}）")
            
            cols_per_row = 3
            for r_i in range(0, len(sampled_df), cols_per_row):
                row_slice = sampled_df.iloc[r_i:r_i + cols_per_row]
                grid_cols = st.columns(cols_per_row)
                for c_idx, (_, row) in enumerate(row_slice.iterrows()):
                    render_exercise_card(row, grid_cols[c_idx])


# ==============================================================================
# TAB 3: 自动生成一周均衡课表
# ==============================================================================
with tab_weekly_plan:
    st.subheader("📅 自动生成一周均衡课表 (Weekly Workout Routine)")
    st.caption("按选定器械条件，自动科学排布每周各肌群负荷。")
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        weekly_days = st.select_slider("1. 每周训练天数", options=[3, 4, 5, 6], value=4)
        actions_per_day = st.slider("2. 每日动作数量", min_value=3, max_value=8, value=5)
    with col_w2:
        all_equipments_clean = sorted([e for e in df['equipment'].dropna().unique() if e])
        weekly_equipments = st.multiselect(
            "3. 健身房/家庭可用器械 (留空代表全部器械)",
            options=all_equipments_clean,
            format_func=fmt_equipment,
            key="weekly_equip",
            default=[]
        )
    
    weekly_structures = {
        3: [
            ("Day 1: 推力主导日 (Push Day)", ["pectorals", "delts", "triceps"], ["chest", "shoulders"]),
            ("Day 2: 拉力主导日 (Pull Day)", ["lats", "upper back", "biceps", "traps"], ["back"]),
            ("Day 3: 下肢与核心日 (Legs & Core)", ["quads", "hamstrings", "glutes", "calves", "abs"], ["upper legs", "waist"])
        ],
        4: [
            ("Day 1: 上肢力量日 (Upper Body A)", ["pectorals", "lats", "delts", "biceps", "triceps"], ["chest", "back", "shoulders"]),
            ("Day 2: 下肢与核心日 (Lower Body A)", ["quads", "hamstrings", "glutes", "calves", "abs"], ["upper legs", "lower legs", "waist"]),
            ("Day 3: 上肢肌肥大日 (Upper Body B)", ["pectorals", "lats", "upper back", "delts", "arms"], ["chest", "back", "upper arms"]),
            ("Day 4: 下肢强化日 (Lower Body B)", ["quads", "hamstrings", "glutes", "calves"], ["upper legs", "lower legs"])
        ],
        5: [
            ("Day 1: 胸部与肱三头 (Chest & Triceps)", ["pectorals", "triceps", "serratus anterior"], ["chest", "upper arms"]),
            ("Day 2: 背部与肱二头 (Back & Biceps)", ["lats", "upper back", "traps", "biceps"], ["back", "upper arms"]),
            ("Day 3: 腿部主导日 (Leg Day)", ["quads", "hamstrings", "glutes", "calves"], ["upper legs", "lower legs"]),
            ("Day 4: 肩部与腰腹 (Shoulders & Abs)", ["delts", "abs", "spine"], ["shoulders", "waist"]),
            ("Day 5: 全身弱项强化/功能性日 (Full Body)", ["pectorals", "lats", "quads", "glutes", "delts"], ["chest", "back", "upper legs"])
        ],
        6: [
            ("Day 1: Push A (推力 力量)", ["pectorals", "delts", "triceps"], ["chest", "shoulders"]),
            ("Day 2: Pull A (拉力 力量)", ["lats", "upper back", "biceps"], ["back", "upper arms"]),
            ("Day 3: Legs A (下肢 力量)", ["quads", "hamstrings", "glutes", "calves"], ["upper legs"]),
            ("Day 4: Push B (推力 肌肥大)", ["pectorals", "delts", "triceps"], ["chest", "shoulders"]),
            ("Day 5: Pull B (拉力 肌肥大)", ["lats", "upper back", "traps", "biceps"], ["back", "upper arms"]),
            ("Day 6: Legs B (下肢/核心 肌肥大)", ["quads", "hamstrings", "glutes", "abs"], ["upper legs", "waist"])
        ]
    }

    if st.button("🚀 生成整周课表", type="primary"):
        # 全局基础器械池硬过滤
        if weekly_equipments:
            base_equipment_pool = df[df['equipment'].isin(weekly_equipments)].copy()
        else:
            base_equipment_pool = df.copy()

        plan_structure = weekly_structures[weekly_days]
        markdown_export = f"# 🏋️‍♂️ 每周 {weekly_days} 天训练计划表\n\n"
        
        st.markdown(f"### 📋 生成结果：每周 {weekly_days} 天训练排期")
        
        for day_title, target_list, bp_list in plan_structure:
            st.markdown(f"<div class='workout-day-box'><h4>📌 {day_title}</h4></div>", unsafe_allow_html=True)
            markdown_export += f"## {day_title}\n"
            
            # 严格从器械池中做部位匹配
            mask = (base_equipment_pool['target'].isin(target_list)) | (base_equipment_pool['body_part'].isin(bp_list))
            day_pool = base_equipment_pool[mask]
            
            if day_pool.empty:
                st.warning(f"{day_title}：在所选器械（{', '.join([fmt_equipment(e) for e in weekly_equipments]) if weekly_equipments else '全部'}）下未找到匹配动作。")
            else:
                sample_count = min(actions_per_day, len(day_pool))
                day_sampled = day_pool.sample(n=sample_count, random_state=random.randint(1, 9999))
                
                d_cols = st.columns(sample_count)
                for idx, (_, row) in enumerate(day_sampled.iterrows()):
                    with d_cols[idx]:
                        st.markdown(f"**{idx+1}. {str(row['name']).title()}**")
                        st.caption(f"{fmt_target(row.get('target',''))} | {fmt_equipment(row.get('equipment',''))}")
                        
                        media_path = row.get('gif_url') or row.get('gifUrl') or row.get('image') or ''
                        if media_path:
                            media_url = media_path if str(media_path).startswith("http") else f"{REPO_RAW_BASE}/{str(media_path).lstrip('/')}"
                            st.image(media_url, use_container_width=True)
                            
                    markdown_export += f"- **动作 {idx+1}**: {str(row['name']).title()} ({fmt_target(row.get('target',''))} / {fmt_equipment(row.get('equipment',''))})\n"
            
            markdown_export += "\n"
            st.divider()

        st.download_button(
            label="📥 下载整周课表 (Markdown 文本格式)",
            data=markdown_export,
            file_name="weekly_fitness_plan.md",
            mime="text/markdown"
        )
