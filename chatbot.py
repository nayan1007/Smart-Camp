import re
from datetime import datetime, timedelta

class SmartRentalChatbot:
    """
    Intelligent Campus Rental Assistant Chatbot.
    Understands student natural language queries, budget limits, device types,
    and returns contextual conversational responses with clickable device booking cards.
    """

    FAQ_RESPONSES = {
        'return_policy': {
            'keywords': ['how to return', 'return process', 'return device', 'return laptop', 'return policy'],
            'reply': (
                "To return a device:\n"
                "1. Go to **Active Rentals** on your dashboard and click **Return Device**.\n"
                "2. Snap clear photos of the device from top, front, and screen.\n"
                "3. Our AI will automatically verify physical integrity against checkout baseline.\n"
                "4. Hand the device over to the Lab Tech Desk (Room 101) where staff will scan your QR pass!"
            )
        },
        'fines': {
            'keywords': ['fine', 'late fee', 'penalty', 'overdue', 'charges'],
            'reply': (
                "Late returns incur a fee of **₹50 per day**. If equipment incurs physical damage or missing components, "
                "our AI vision inspection calculates a repair assessment fine which is reviewed by the Lab Manager. "
                "You can inspect and pay any pending dues in the **Fines & Invoices** tab."
            )
        },
        'location': {
            'keywords': ['where', 'location', 'tech desk', 'room', 'pickup', 'office'],
            'reply': (
                "Equipment issue & return desks are located at:\n"
                "• **Main Campus Tech Desk**: Room 101, Central Administrative Block\n"
                "• **Engineering Hardware Lab**: Room 204, Block B\n"
                "• **Media & Visual Arts Studio**: Room 305, Arts Annex\n"
                "Hours: Mon - Fri (8:30 AM – 6:30 PM), Sat (9:00 AM – 1:00 PM)."
            )
        },
        'damage_ai': {
            'keywords': ['damage detection', 'how does ai work', 'crack', 'scratch', 'ai damage'],
            'reply': (
                "Our Smart Campus platform uses Computer Vision to compare high-resolution photos taken before you check out "
                "with photos taken upon return. It highlights localized surface changes, cracks, or scratches and estimates a repair score "
                "to ensure fair, transparent evaluations for all students!"
            )
        }
    }

    def process_message(self, message_text, db_session, models):
        """
        Processes a student query and generates text + interactive device action cards.
        """
        text = message_text.strip().lower()
        Device = models['Device']
        DeviceCategory = models['DeviceCategory']

        # 1. Check FAQs first
        for faq_key, faq_data in self.FAQ_RESPONSES.items():
            for kw in faq_data['keywords']:
                if kw in text:
                    return {
                        'text': faq_data['reply'],
                        'device_cards': []
                    }

        # 2. Extract constraints
        budget = self._extract_budget(text)
        category_name = self._extract_category(text)
        timing = self._extract_timing(text)

        # 3. Query Database
        query = db_session.query(Device)

        if category_name:
            cat = db_session.query(DeviceCategory).filter(DeviceCategory.name.ilike(f"%{category_name}%")).first()
            if cat:
                query = query.filter(Device.category_id == cat.id)

        if budget:
            query = query.filter(Device.price_per_day <= budget)

        # Prioritize available devices
        matching_devices = query.all()
        # Sort so available come first, then sorted by price
        matching_devices.sort(key=lambda d: (d.status != 'available', d.price_per_day))

        # 4. Formulate Response
        cards = []
        for dev in matching_devices[:4]:
            cards.append({
                'id': dev.id,
                'code': dev.device_code,
                'name': dev.name,
                'brand': dev.brand,
                'model': dev.model,
                'price_per_day': dev.price_per_day,
                'status': dev.status,
                'specs': dev.specs,
                'image_url': dev.image_url or '/static/images/devices/default.jpg',
                'location': dev.location
            })

        if not matching_devices:
            # Fallback suggestion
            all_avail = db_session.query(Device).filter_by(status='available').limit(3).all()
            fallback_cards = [{
                'id': d.id,
                'code': d.device_code,
                'name': d.name,
                'brand': d.brand,
                'price_per_day': d.price_per_day,
                'status': d.status,
                'specs': d.specs,
                'image_url': d.image_url,
                'location': d.location
            } for d in all_avail]

            reply_text = (
                f"I couldn't find exact matches for your requested filter"
                f"{f' under ₹{budget}' if budget else ''}"
                f"{f' in {category_name}' if category_name else ''}. "
                f"Here are some popular available items you might like:"
            )
            return {
                'text': reply_text,
                'device_cards': fallback_cards
            }

        # Crafted response
        timing_str = f" for {timing}" if timing else ""
        budget_str = f" within ₹{budget:.0f}/day" if budget else ""
        category_str = f" {category_name}" if category_name else " devices"

        reply_text = (
            f"Here are the top matches I found{category_str}{budget_str}{timing_str}. "
            f"You can review their specs and reserve immediately:"
        )

        return {
            'text': reply_text,
            'device_cards': cards
        }

    @staticmethod
    def _extract_budget(text):
        m = re.search(r'(?:under|for|below|within|budget of|₹|\$)\s*(\d+)', text)
        if m:
            return float(m.group(1))
        return None

    @staticmethod
    def _extract_category(text):
        categories = {
            'laptop': 'Laptops',
            'notebook': 'Laptops',
            'macbook': 'Laptops',
            'projector': 'Projectors',
            'camera': 'Cameras',
            'dslr': 'Cameras',
            'tablet': 'Tablets',
            'ipad': 'Tablets',
            'oscilloscope': 'Lab Equipment',
            'arduino': 'Lab Equipment',
            'raspberry': 'Lab Equipment',
            'multimeter': 'Lab Equipment',
            'headphones': 'Accessories',
            'charger': 'Accessories',
            'adapter': 'Accessories'
        }
        for kw, cat in categories.items():
            if kw in text:
                return cat
        return None

    @staticmethod
    def _extract_timing(text):
        if 'tomorrow' in text:
            return 'tomorrow'
        if 'monday' in text:
            return 'Monday'
        if 'today' in text:
            return 'today'
        if 'next week' in text:
            return 'next week'
        return None
