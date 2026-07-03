# src/agent.py - FINAL WORKING VERSION

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass, asdict
from enum import Enum

from groq import Groq
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER
from dotenv import load_dotenv

load_dotenv()

class TripStyle(Enum):
    BUDGET = "budget"
    LUXURY = "luxury"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    RELAXATION = "relaxation"
    FOODIE = "foodie"

@dataclass
class TripRequest:
    destination: str
    start_date: str
    end_date: str
    budget: float
    travelers: int
    style: TripStyle
    interests: List[str]
    departure_city: str = ""

class VoyageFalconEnhanced:
    
    def __init__(self):
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY not found")
        self.client = Groq(api_key=groq_key)
        self.model = "llama-3.3-70b-versatile"
        self.weather_key = os.getenv("OPENWEATHER_API_KEY", "")
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.memory = []
        self.current_trip = None
        self.system_prompt = "You are VoyageFalcon, an expert trip planner. You MUST respond with ONLY valid JSON. No markdown, no explanations. Just pure JSON."

    def _call_ai(self, prompt, expect_json=True):
        """Call Groq AI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            
            if expect_json:
                # Clean the response to get pure JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON object
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    content = content[start:end]
                
                return json.loads(content)
            
            return content
            
        except Exception as e:
            print(f"AI Error: {e}")
            if expect_json:
                return {}
            return "Error generating response."

    def plan_trip(self, request: TripRequest) -> Dict:
        print("🦅 Planning trip...")
        
        # Weather (try real, fallback to AI)
        weather = {"current_temp": "22", "conditions": "pleasant", "forecast": []}
        if self.weather_key:
            try:
                url = "https://nominatim.openstreetmap.org/search"
                r = requests.get(url, params={"q": request.destination, "format": "json", "limit": 1}, headers={"User-Agent": "VoyageFalcon"})
                data = r.json()
                if data:
                    lat, lon = data[0]["lat"], data[0]["lon"]
                    r2 = requests.get("https://api.openweathermap.org/data/2.5/forecast", params={"lat": lat, "lon": lon, "appid": self.weather_key, "units": "metric"})
                    wdata = r2.json()
                    if "list" in wdata:
                        fc = []
                        seen = set()
                        for item in wdata["list"]:
                            d = item["dt_txt"][:10]
                            if d not in seen:
                                seen.add(d)
                                fc.append({"date": item["dt_txt"], "temp": round(item["main"]["temp"],1), "description": item["weather"][0]["description"]})
                        weather = {"current_temp": fc[0]["temp"], "conditions": fc[0]["description"], "forecast": fc[:7]}
            except:
                pass
        
        # Photos
        photos = []
        if self.unsplash_key:
            try:
                r = requests.get("https://api.unsplash.com/search/photos", params={"query": f"{request.destination} travel", "per_page": 5, "client_id": self.unsplash_key})
                for p in r.json().get("results", []):
                    photos.append({"url": p["urls"]["regular"], "photographer": p["user"]["name"]})
            except:
                pass
        
        print("📋 Generating itinerary...")
        itinerary = self._generate_itinerary(request, weather)
        
        print("✈️ Finding flights...")
        flights = self._get_flights(request)
        
        print("🏨 Finding hotels...")
        hotels = self._get_hotels(request)
        
        print("💡 Getting tips...")
        tips = self._get_tips(request)
        
        print("🎒 Packing...")
        packing = self._get_packing(request, weather)
        
        print("💰 Budget...")
        budget = self._calculate_budget(request, flights, hotels)
        
        trip_plan = {
            "request": asdict(request),
            "weather": weather,
            "photos": photos,
            "flights": flights,
            "hotels": hotels,
            "itinerary": itinerary,
            "budget": budget,
            "packing_list": packing,
            "local_tips": tips
        }
        
        self.current_trip = trip_plan
        print("✅ Done!")
        return trip_plan

    def _generate_itinerary(self, request, weather):
        s = datetime.strptime(request.start_date, "%Y-%m-%d")
        e = datetime.strptime(request.end_date, "%Y-%m-%d")
        days = (e - s).days + 1
        
        prompt = f"""Create a {days}-day detailed itinerary for {request.destination}.
        Style: {request.style.value}
        Interests: {', '.join(request.interests)}
        Budget: ${request.budget}
        Weather: {weather.get('conditions', 'pleasant')}

        Return ONLY valid JSON with this exact structure:
        {{"days": [
            {{
                "day": 1,
                "theme": "Exciting title for day 1",
                "activities": [
                    {{"time": "09:00 AM", "name": "Activity name", "location": "Place name", "cost": 50}},
                    {{"time": "11:00 AM", "name": "Another activity", "location": "Location", "cost": 30}}
                ],
                "meals": [
                    {{"type": "Breakfast", "suggestion": "Restaurant name - dish name", "cost": 15}},
                    {{"type": "Lunch", "suggestion": "Restaurant name - dish name", "cost": 25}},
                    {{"type": "Dinner", "suggestion": "Restaurant name - dish name", "cost": 40}}
                ],
                "tips": ["Tip 1", "Tip 2"]
            }}
        ]}}
        
        Use REAL places, restaurants, and realistic prices in USD."""
        
        result = self._call_ai(prompt)
        if 'days' not in result:
            print("WARNING: No 'days' in itinerary response, creating default")
            return {"days": []}
        return result

    def _get_flights(self, request):
        prompt = f"""Find 3 realistic flights from {request.departure_city} to {request.destination}.
        
        Return ONLY valid JSON:
        {{"flights": [
            {{"airline": "Airline name", "departure_time": "2025-01-15 08:00", "arrival_time": "2025-01-15 16:30", "duration": "8h 30m", "stops": 0, "price": 450}},
            {{"airline": "Airline name", "departure_time": "2025-01-15 14:00", "arrival_time": "2025-01-16 02:00", "duration": "12h", "stops": 1, "price": 380}},
            {{"airline": "Airline name", "departure_time": "2025-01-15 22:00", "arrival_time": "2025-01-16 06:30", "duration": "8h 30m", "stops": 0, "price": 520}}
        ]}}"""
        
        result = self._call_ai(prompt)
        return result.get('flights', [])

    def _get_hotels(self, request):
        days = (datetime.strptime(request.end_date, "%Y-%m-%d") - datetime.strptime(request.start_date, "%Y-%m-%d")).days
        per_night = request.budget * 0.3 / max(days, 1)
        
        prompt = f"""Recommend 5 hotels in {request.destination} under ${per_night:.0f}/night.
        
        Return ONLY valid JSON:
        {{"hotels": [
            {{"name": "Real hotel name", "neighborhood": "Area name", "price_per_night": 120, "rating": 4.3, "amenities": ["Free WiFi", "Pool", "Gym"]}}
        ]}}"""
        
        result = self._call_ai(prompt)
        return result.get('hotels', [])

    def _get_tips(self, destination):
        prompt = f"""Give travel tips for {destination}. Return ONLY valid JSON:
        {{"dos_donts": ["rule 1", "rule 2", "rule 3", "rule 4", "rule 5"],
          "phrases": ["phrase1 - translation", "phrase2 - translation"],
          "scams": ["scam 1", "scam 2", "scam 3"],
          "tipping": "Tipping customs explanation",
          "transport": ["tip 1", "tip 2", "tip 3", "tip 4"],
          "emergencies": ["Police: 110", "Ambulance: 119"]}}"""
        
        return self._call_ai(prompt)

    def _get_packing(self, request, weather):
        prompt = f"""Create packing list for {request.destination}. Weather: {weather.get('conditions', 'mild')}. Return ONLY valid JSON:
        {{"categories": [
            {{"name": "Clothing", "items": ["item 1", "item 2", "item 3", "item 4"]}},
            {{"name": "Footwear", "items": ["item 1", "item 2"]}},
            {{"name": "Electronics", "items": ["item 1", "item 2", "item 3"]}},
            {{"name": "Toiletries", "items": ["item 1", "item 2", "item 3", "item 4"]}},
            {{"name": "Documents", "items": ["item 1", "item 2", "item 3"]}},
            {{"name": "Health", "items": ["item 1", "item 2"]}},
            {{"name": "Miscellaneous", "items": ["item 1", "item 2", "item 3"]}}
        ]}}"""
        
        return self._call_ai(prompt)

    def _calculate_budget(self, request, flights, hotels):
        days = (datetime.strptime(request.end_date, "%Y-%m-%d") - datetime.strptime(request.start_date, "%Y-%m-%d")).days + 1
        
        fp = 500
        if flights:
            try: fp = float(flights[0].get('price', 500))
            except: pass
        
        hp = 150
        if hotels:
            try: hp = float(hotels[0].get('price_per_night', 150))
            except: pass
        
        df = 40
        da = 30
        
        ft = fp * request.travelers
        ht = hp * days
        fot = df * days * request.travelers
        at = da * days
        tr = 20 * days
        mi = request.budget * 0.1
        total = ft + ht + fot + at + tr + mi
        
        return {
            "flights": round(ft, 2),
            "accommodation": round(ht, 2),
            "food_dining": round(fot, 2),
            "activities": round(at, 2),
            "transportation": round(tr, 2),
            "miscellaneous": round(mi, 2),
            "total_estimated": round(total, 2),
            "daily_breakdown": round(total/days, 2),
            "budget_remaining": round(request.budget - total, 2),
            "status": "under_budget" if total <= request.budget else "over_budget"
        }

    def chat(self, message):
        return self._call_ai(message, expect_json=False)

    def export_to_pdf(self, trip_plan, filename="trip.pdf"):
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        ts = ParagraphStyle('T', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1a73e8'), spaceAfter=20, alignment=TA_CENTER)
        hs = ParagraphStyle('H', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2c3e50'), spaceBefore=12, spaceAfter=8)
        ns = ParagraphStyle('N', parent=styles['Normal'], fontSize=10, leading=14)
        
        story = []
        r = trip_plan['request']
        
        story.append(Spacer(1, 50))
        story.append(Paragraph("VOYAGEFALCON", ts))
        story.append(Paragraph(f"Trip to {r['destination']}", hs))
        story.append(Paragraph(f"{r['start_date']} to {r['end_date']}", ns))
        story.append(PageBreak())
        
        # Itinerary
        story.append(Paragraph("ITINERARY", hs))
        for day in trip_plan.get('itinerary', {}).get('days', []):
            story.append(Paragraph(f"Day {day.get('day','')}: {day.get('theme','')}", hs))
            for a in day.get('activities', []):
                story.append(Paragraph(f"  {a.get('time','')} - {a.get('name','')} at {a.get('location','')} (${a.get('cost',0)})", ns))
            for m in day.get('meals', []):
                story.append(Paragraph(f"  {m.get('type','')}: {m.get('suggestion','')}", ns))
            story.append(Spacer(1, 8))
        story.append(PageBreak())
        
        # Flights
        story.append(Paragraph("FLIGHTS", hs))
        for f in trip_plan.get('flights', []):
            story.append(Paragraph(f"{f.get('airline','')}: {f.get('departure_time','')} to {f.get('arrival_time','')} | {f.get('duration','')} | ${f.get('price','')}", ns))
        story.append(PageBreak())
        
        # Hotels
        story.append(Paragraph("HOTELS", hs))
        for h in trip_plan.get('hotels', []):
            story.append(Paragraph(f"{h.get('name','')} - {h.get('neighborhood','')} | ${h.get('price_per_night','')}/night | {h.get('rating','')}/5", ns))
        story.append(PageBreak())
        
        # Budget
        story.append(Paragraph("BUDGET", hs))
        for k,v in trip_plan.get('budget', {}).items():
            if isinstance(v, (int,float)):
                story.append(Paragraph(f"{k.replace('_',' ').title()}: ${v:,.2f}", ns))
        
        doc.build(story)
        return filename