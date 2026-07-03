import streamlit as st
import sys, os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from agent import VoyageFalconEnhanced, TripRequest, TripStyle

st.set_page_config(page_title="VoyageFalcon", page_icon="🦅", layout="wide")

st.markdown("""
<style>
.main-title {font-size:3rem;background:linear-gradient(120deg,#1a73e8,#34a853);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;font-weight:800}
.stButton button {background:linear-gradient(120deg,#1a73e8,#1557b0);color:white;font-weight:bold;padding:0.75rem;border-radius:10px;border:none}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🦅 VoyageFalcon</p>', unsafe_allow_html=True)

@st.cache_resource
def get_agent():
    return VoyageFalconEnhanced()

agent = get_agent()

with st.sidebar:
    st.header("✈️ Plan Your Trip")
    destination = st.text_input("🌍 Destination", "Tokyo, Japan")
    departure = st.text_input("🏠 From", "New York, USA")
    c1,c2 = st.columns(2)
    with c1: start = st.date_input("Start", datetime.now()+timedelta(days=30))
    with c2: end = st.date_input("End", start+timedelta(days=5))
    budget = st.slider("💰 Budget", 500, 20000, 3000, 500)
    travelers = st.number_input("👥 Travelers", 1, 10, 1)
    style = st.selectbox("🎯 Style", [s.value for s in TripStyle])
    interests = st.multiselect("❤️ Interests", ["Food & Dining","History & Culture","Nature","Shopping","Nightlife","Art & Museums","Adventure"], default=["Food & Dining","History & Culture"])
    
    if st.button("🦅 Plan My Trip!", type="primary", use_container_width=True):
        with st.spinner("Planning..."):
            req = TripRequest(destination=destination, start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"), budget=float(budget), travelers=travelers, style=TripStyle(style), interests=interests, departure_city=departure)
            st.session_state.trip = agent.plan_trip(req)
            st.session_state.planned = True
        st.rerun()

if st.session_state.get('planned'):
    trip = st.session_state.trip
    
    # Download PDF
    if st.button("📥 Download PDF"):
        fn = f"exports/trip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        agent.export_to_pdf(trip, fn)
        with open(fn, "rb") as f: st.download_button("Download", f.read(), os.path.basename(fn), "application/pdf")
    
    # Photos
    if trip.get('photos'):
        st.subheader("📸 Destination")
        cols = st.columns(len(trip['photos']))
        for i, p in enumerate(trip['photos']):
            with cols[i]: st.image(p['url'], use_container_width=True)
    st.markdown("---")
    
    # TABS
    tabs = st.tabs(["📋 Itinerary", "✈️ Flights", "🏨 Hotels", "💰 Budget", "🌤️ Weather", "💡 Tips & Packing"])
    
    with tabs[0]:
        st.header("Your Itinerary")
        days = trip.get('itinerary', {}).get('days', [])
        if days:
            for day in days:
                with st.expander(f"Day {day.get('day','')}: {day.get('theme','')}", expanded=True):
                    st.subheader("📍 Activities")
                    for a in day.get('activities', []):
                        st.write(f"**{a.get('time','')}** - {a.get('name','')} | 📍 {a.get('location','')} | 💰 ${a.get('cost',0)}")
                    
                    if day.get('meals'):
                        st.subheader("🍽️ Dining")
                        for m in day['meals']:
                            st.write(f"• **{m.get('type','')}**: {m.get('suggestion','')} (~${m.get('cost',0)})")
                    
                    if day.get('tips'):
                        st.subheader("💡 Tips")
                        for t in day['tips']: st.info(t)
        else:
            st.warning("Itinerary not generated. Please try again.")
    
    with tabs[1]:
        st.header("Flights")
        flights = trip.get('flights', [])
        if flights:
            for i, f in enumerate(flights, 1):
                st.subheader(f"Option {i}: {f.get('airline','Airline')}")
                c1,c2 = st.columns(2)
                with c1: st.write(f"🛫 Depart: {f.get('departure_time','N/A')}")
                with c2: st.write(f"🛬 Arrive: {f.get('arrival_time','N/A')}")
                c1,c2,c3 = st.columns(3)
                with c1: st.metric("Duration", f.get('duration','N/A'))
                with c2: st.metric("Stops", f.get('stops',0))
                with c3: st.metric("Price", f"${f.get('price','N/A')}")
                st.divider()
        else:
            st.warning("No flights generated. Try again.")
    
    with tabs[2]:
        st.header("Hotels")
        hotels = trip.get('hotels', [])
        if hotels:
            for h in hotels:
                c1,c2 = st.columns([3,1])
                with c1:
                    st.subheader(h.get('name','Hotel'))
                    st.write(f"📍 {h.get('neighborhood','')} | ⭐ {h.get('rating','N/A')}")
                    if h.get('amenities'): st.write(f"🏨 {', '.join(h['amenities'])}")
                with c2: st.metric("Per Night", f"${h.get('price_per_night','N/A')}")
                st.divider()
        else:
            st.warning("No hotels generated. Try again.")
    
    with tabs[3]:
        st.header("Budget")
        b = trip.get('budget', {})
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("Total", f"${b.get('total_estimated',0):,.2f}")
        with c2: st.metric("Per Day", f"${b.get('daily_breakdown',0):,.2f}")
        with c3:
            rem = b.get('budget_remaining',0)
            st.metric("Remaining", f"${rem:,.2f}", delta="Under budget!" if rem>0 else "Over budget")
        
        for k,v in b.items():
            if isinstance(v,(int,float)) and k not in ['daily_breakdown','status']:
                pct = max(0.0, min(v/b.get('total_estimated',1), 1.0))
                st.progress(pct, text=f"{k.replace('_',' ').title()}: ${v:,.2f}")
    
    with tabs[4]:
        st.header("Weather")
        w = trip.get('weather', {})
        if w.get('current_temp'):
            st.info(f"🌡️ {w.get('current_temp','')}°C | {w.get('conditions','').title()} | 💧 {w.get('humidity','')}%")
            if w.get('forecast'):
                st.subheader("Forecast")
                for f in w['forecast'][:5]:
                    c1,c2 = st.columns([3,1])
                    with c1: st.write(f"**{f.get('date','')[:10]}** - {f.get('description','').title()}")
                    with c2: st.write(f"🌡️ {f.get('temp','')}°C")
    
    with tabs[5]:
        st.header("Travel Tips")
        tips = trip.get('local_tips', {})
        for k,v in tips.items():
            with st.expander(k.replace('_',' ').title()):
                if isinstance(v, list):
                    for i in v: st.write(f"• {i}")
                else: st.write(v)
        
        st.header("Packing List")
        for cat in trip.get('packing_list', {}).get('categories', []):
            with st.expander(cat.get('name','Category')):
                for item in cat.get('items', []):
                    st.checkbox(item, key=f"pack_{item}")

else:
    st.info("👈 Enter your trip details and click **Plan My Trip!**")