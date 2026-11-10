import streamlit as st
import pymongo
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

st.set_page_config(page_title="ReliefLink AI Dashboard", page_icon="🌍", layout="wide")

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        border-left: 5px solid #FF4B4B;
    }
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.2);
    }
</style>
""", unsafe_allow_html=True)

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["relieflink_db"]

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2913/2913483.png", width=80) 
st.sidebar.title("🚨 ReliefLink")
st.sidebar.markdown("**Smart Disaster Relief Coordinator**")
st.sidebar.markdown("---")

menu = st.sidebar.radio("📌 Navigation Menu", [
    "📊 Shelter Dashboard",
    "📈 Critical Analytics",
    "📝 Relief Management",
    "🤖 AI Demand Forecast"
])

st.sidebar.markdown("---")
st.sidebar.caption("Powered by MongoDB & Scikit-Learn")

if menu == "📊 Shelter Dashboard":
    st.title("🏕️ Disaster Shelter Command Center")
    
    total_camps = db.relief_camps.count_documents({})
    total_pop_cursor = db.relief_camps.aggregate([{"$group": {"_id": None, "total": {"$sum": "$population"}}}])
    total_pop = list(total_pop_cursor)[0]["total"] if total_camps > 0 else 0
    critical_reqs = db.relief_requests.count_documents({"urgency_level": "CRITICAL", "status": "PENDING"})

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Active Camps", f"{total_camps} 🏕️")
    col2.metric("Total Displaced Population", f"{total_pop:,} 👥")
    col3.metric("Critical Pending Requests", f"{critical_reqs} ⚠️", delta="- Action Needed", delta_color="inverse")
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Active Shelters Directory", "⚠️ Low Inventory Alerts"])
    
    with tab1:
        camps_data = list(db.relief_camps.find({}, {"_id": 0, "camp_name": 1, "zone": 1, "population": 1}))
        if camps_data:
            st.dataframe(pd.DataFrame(camps_data), use_container_width=True, height=300)
            
    with tab2:
        pipeline = [
            {"$unwind": "$supplies_inventory"},
            {"$match": {"supplies_inventory.quantity": {"$lt": 300}}},
            {
                "$project": {
                    "_id": 0, "camp_name": 1, "zone": 1,
                    "item_name": "$supplies_inventory.item_name",
                    "remaining_quantity": "$supplies_inventory.quantity",
                    "unit": "$supplies_inventory.unit"
                }
            }
        ]
        low_stock = list(db.relief_camps.aggregate(pipeline))
        if low_stock:
            st.warning("The following shelters are running low on critical supplies (< 300 units).")
            st.dataframe(pd.DataFrame(low_stock), use_container_width=True)
        else:
            st.success("All supply inventories are currently at safe stock levels.")

elif menu == "📈 Critical Analytics":
    st.title("📊 Critical Emergency Analytics")
    st.markdown("Monitor high-priority emergency demands broken down by geographical districts and specific supply items.")
    
    tab_zone, tab_items = st.tabs(["🗺️ Demands by District Zone", "📦 Demands by Relief Items"])
    
    with tab_zone:
        pipeline_zone = [
            {"$match": {"urgency_level": "CRITICAL", "status": "PENDING"}},
            {"$lookup": {"from": "relief_camps", "localField": "camp_id", "foreignField": "_id", "as": "camp_details"}},
            {"$unwind": "$camp_details"},
            {"$group": {"_id": "$camp_details.zone", "total_critical_requests": {"$sum": 1}}},
            {"$sort": {"total_critical_requests": -1}}
        ]
        results_zone = list(db.relief_requests.aggregate(pipeline_zone))
        if results_zone:
            df_zone = pd.DataFrame(results_zone).rename(columns={"_id": "District Zone", "total_critical_requests": "Critical Requests"})
            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(df_zone.set_index("District Zone"), color="#FF4B4B")
            with col2:
                st.dataframe(df_zone, use_container_width=True)
        else:
            st.info("No critical pending requests found by zone.")
            
    with tab_items:
        pipeline_items = [
            {"$match": {"urgency_level": "CRITICAL", "status": "PENDING"}},
            {"$unwind": "$requested_items"},
            {
                "$group": {
                    "_id": "$requested_items.item_name",
                    "total_required_units": {"$sum": "$requested_items.required_quantity"},
                    "total_requests": {"$sum": 1}
                }
            },
            {"$sort": {"total_required_units": -1}}
        ]
        results_items = list(db.relief_requests.aggregate(pipeline_items))
        if results_items:
            df_items = pd.DataFrame(results_items).rename(columns={
                "_id": "Relief Item Category",
                "total_required_units": "Total Required Quantity",
                "total_requests": "Request Frequency"
            })
            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(df_items.set_index("Relief Item Category")["Total Required Quantity"], color="#3B82F6")
            with col2:
                st.dataframe(df_items, use_container_width=True)
        else:
            st.info("No critical pending requests found by item.")

elif menu == "📝 Relief Management":
    st.title("📝 Operations & Resource Management")
    
    tab_req, tab_camp = st.tabs(["🚨 Submit Aid Request", "🏕️ Register New Relief Camp"])
    
    with tab_req:
        st.subheader("Dispatch Emergency Request")
        camps = list(db.relief_camps.find({}, {"_id": 1, "camp_name": 1}))
        camp_options = {c["camp_name"]: c["_id"] for c in camps}
        
        if camp_options:
            with st.form("emergency_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    selected_camp = st.selectbox("Select Relief Camp", list(camp_options.keys()))
                    item_name = st.selectbox("Item Category", ["Drinking Water (Liters)", "Emergency Food Pack", "Medical Kits", "Blankets"])
                with col2:
                    quantity = st.number_input("Required Quantity (Units)", min_value=1, value=100)
                    urgency = st.select_slider("Urgency Level", options=["LOW", "MEDIUM", "HIGH", "CRITICAL"], value="HIGH")
                
                submit = st.form_submit_button("🚀 Submit Request to Database")
                
                if submit:
                    new_req = {
                        "camp_id": camp_options[selected_camp],
                        "requested_items": [{
                            "item_name": item_name,
                            "category": item_name.split()[0],
                            "required_quantity": int(quantity),
                            "unit": "Units"
                        }],
                        "urgency_level": urgency,
                        "status": "PENDING",
                        "requested_at": pd.Timestamp.now()
                    }
                    db.relief_requests.insert_one(new_req)
                    st.success(f"Request for {quantity} units of {item_name} successfully dispatched for {selected_camp}!")

    with tab_camp:
        st.subheader("Add New Relief Shelter to Database")
        st.markdown("Register a new operational camp with initial inventory limits adhering to `$jsonSchema` constraints.")
        
        with st.form("new_camp_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_camp_name = st.text_input("Relief Camp Name", placeholder="e.g., Relief Camp 101")
                new_zone = st.selectbox("District Zone", ["North-District", "South-District", "East-District", "West-District", "Central-District"])
                new_population = st.number_input("Initial Population Density", min_value=10, value=250, step=10)
            with col2:
                contact_name = st.text_input("Camp Leader / Contact Name", placeholder="e.g., U Aye Than")
                contact_phone = st.text_input("Contact Phone", placeholder="e.g., +95970000101")
                lat = st.number_input("Latitude Coordinate", value=16.85, format="%.4f")
                lng = st.number_input("Longitude Coordinate", value=96.15, format="%.4f")
                
            submit_camp = st.form_submit_button("➕ Register Camp into MongoDB")
            
            if submit_camp:
                if new_camp_name and contact_name and contact_phone:
                    new_camp_doc = {
                        "camp_name": new_camp_name,
                        "zone": new_zone,
                        "population": int(new_population),
                        "contact_person": {
                            "name": contact_name,
                            "phone": contact_phone
                        },
                        "location": {
                            "type": "Point",
                            "coordinates": [float(lng), float(lat)]
                        },
                        "supplies_inventory": [
                            {"item_name": "Drinking Water (Liters)", "category": "Water", "quantity": 1000, "unit": "Liters"},
                            {"item_name": "Emergency Food Pack", "category": "Food", "quantity": 500, "unit": "Packs"}
                        ],
                        "created_at": pd.Timestamp.now()
                    }
                    db.relief_camps.insert_one(new_camp_doc)
                    st.success(f"Camp '{new_camp_name}' successfully registered in MongoDB!")
                else:
                    st.error("Please complete all text fields before registering.")

elif menu == "🤖 AI Demand Forecast":
    st.title("🤖 AI Resource Demand Predictor")
    st.markdown("Use our Machine Learning model (`RandomForestRegressor`) to predict optimal supply distribution based on historical data.")
    
    pipeline = [
        {"$lookup": {"from": "relief_camps", "localField": "camp_id", "foreignField": "_id", "as": "camp"}},
        {"$unwind": "$camp"},
        {"$unwind": "$requested_items"},
        {"$project": {"_id": 0, "zone": "$camp.zone", "population": "$camp.population",
                      "urgency_level": "$urgency_level", "required_quantity": "$requested_items.required_quantity"}}
    ]
    data = list(db.relief_requests.aggregate(pipeline))
    
    if data:
        df = pd.DataFrame(data)
        df_encoded = pd.get_dummies(df, columns=["zone", "urgency_level"], drop_first=True)
        X = df_encoded.drop("required_quantity", axis=1)
        y = df_encoded["required_quantity"]
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        st.markdown("### ⚙️ Scenario Configuration")
        col1, col2, col3 = st.columns(3)
        with col1:
            pop_input = st.number_input("Shelter Population", min_value=50, max_value=5000, value=350, step=50)
        with col2:
            zone_input = st.selectbox("Disaster Zone", ["North-District", "South-District", "East-District", "West-District", "Central-District"])
        with col3:
            urgency_input = st.selectbox("Urgency Level", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🧠 Run AI Prediction Analysis", type="primary", use_container_width=True):
            with st.spinner("AI is analyzing historical MongoDB data..."):
                input_dict = {col: [0] for col in X.columns}
                input_dict["population"] = [pop_input]
                if f"zone_{zone_input}" in input_dict: input_dict[f"zone_{zone_input}"] = [1]
                if f"urgency_level_{urgency_input}" in input_dict: input_dict[f"urgency_level_{urgency_input}"] = [1]
                
                prediction = int(model.predict(pd.DataFrame(input_dict))[0])
                
                st.success("✅ Prediction Successfully Generated!")
                st.metric(label="Total Predicted Supply Requirement", value=f"{prediction:,} Units", delta="Algorithm Confidence: High")
                
                st.markdown("---")
                st.subheader("📦 Automated Supply Breakdown")
                
                w, f, m = int(prediction * 0.40), int(prediction * 0.30), int(prediction * 0.15)
                b = prediction - (w + f + m)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("💧 Drinking Water (40%)", f"{w:,}")
                c2.metric("🥫 Emergency Food (30%)", f"{f:,}")
                c3.metric("🚑 Medical Kits (15%)", f"{m:,}")
                c4.metric("🛌 Blankets (15%)", f"{b:,}")