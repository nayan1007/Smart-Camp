import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class DeviceRecommender:
    """
    AI-powered Smart Device Recommendation Engine.
    Matches student natural language requirements against device catalog specs, tags,
    pricing, and availability, providing explainable recommendations.
    """

    WORKLOAD_RULES = {
        'ml': {
            'keywords': ['machine learning', 'deep learning', 'ml', 'ai', 'neural', 'pytorch', 'tensorflow', 'data science', 'python'],
            'min_ram': 16,
            'require_gpu': True,
            'preferred_categories': ['Laptops'],
            'reasons': [
                'High RAM (16GB+) for processing large datasets in memory',
                'Dedicated GPU for accelerating model training & CUDA workloads',
                'Multi-core CPU for parallelized data preprocessing in Python'
            ]
        },
        'video_3d': {
            'keywords': ['video editing', '4k', 'rendering', 'blender', 'premiere', 'after effects', 'animation', 'cad', 'autocad'],
            'min_ram': 16,
            'require_gpu': True,
            'preferred_categories': ['Laptops'],
            'reasons': [
                'Discrete graphics GPU provides real-time timeline scrubbing & render acceleration',
                'Sufficient RAM for multi-layer 4K compositions',
                'Fast SSD storage bandwidth for heavy video caches'
            ]
        },
        'presentation': {
            'keywords': ['presentation', 'seminar', 'slides', 'projector', 'pitch', 'conference', 'meeting', 'display', 'screen'],
            'min_ram': 0,
            'require_gpu': False,
            'preferred_categories': ['Projectors', 'Laptops'],
            'reasons': [
                'High lumen output suitable for classroom ambient lighting',
                'HDMI & Wireless screen-casting compatibility',
                'Lightweight and rapid plug-and-play setup'
            ]
        },
        'photography': {
            'keywords': ['camera', 'photo', 'photography', 'shoot', 'fest', 'event', 'dslr', 'recording', 'vlog', 'lens'],
            'min_ram': 0,
            'require_gpu': False,
            'preferred_categories': ['Cameras'],
            'reasons': [
                'High-resolution optical sensor for campus events and portraits',
                'Full HD / 4K video recording with stabilization',
                'Interchangeable lens support for wide angle & zoom coverage'
            ]
        },
        'electronics_lab': {
            'keywords': ['iot', 'arduino', 'raspberry', 'circuit', 'robotics', 'signal', 'oscilloscope', 'soldering', 'microcontroller', 'sensors'],
            'min_ram': 0,
            'require_gpu': False,
            'preferred_categories': ['Lab Equipment'],
            'reasons': [
                'Lab-grade precision measurement and GPIO breadboard support',
                'Full suite of development headers and sensor peripherals included',
                'Ideal for hardware prototyping and semester capstone builds'
            ]
        },
        'casual_study': {
            'keywords': ['notes', 'reading', 'pdf', 'zoom', 'browsing', 'assignment', 'tablet', 'study', 'lightweight', 'ipad'],
            'min_ram': 4,
            'require_gpu': False,
            'preferred_categories': ['Tablets', 'Laptops'],
            'reasons': [
                'All-day battery life for long library study sessions',
                'Lightweight form factor with active stylus/pen support',
                'Crisp display optimized for e-books and research papers'
            ]
        }
    }

    @staticmethod
    def extract_budget(query_text):
        """Extracts max budget if specified like 'under 500' or '₹400' or 'within 300'"""
        match = re.search(r'(?:under|within|below|max|budget of|₹|\$)\s*(\d+)', query_text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def extract_days(query_text):
        """Extracts number of rental days like 'for 10 days' or '5 days'"""
        match = re.search(r'(\d+)\s*(?:day|days)', query_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 7 # default to 1 week estimate

    def recommend(self, query_text, all_devices, top_k=5):
        if not all_devices:
            return []

        lower_query = query_text.lower()
        budget_limit = self.extract_budget(lower_query)
        rental_days = self.extract_days(lower_query)

        # Detect matched workload patterns
        detected_workloads = []
        for wl_key, wl_data in self.WORKLOAD_RULES.items():
            for kw in wl_data['keywords']:
                if kw in lower_query:
                    detected_workloads.append(wl_key)
                    break

        # Compute TF-IDF similarity between query and devices
        corpus = [lower_query]
        device_descriptions = []
        for dev in all_devices:
            specs = dev.specs
            desc = f"{dev.name} {dev.category_rel.name if dev.category_rel else ''} {dev.brand} {dev.model} {dev.tags} "
            desc += " ".join([f"{k} {v}" for k, v in specs.items()])
            device_descriptions.append(desc.lower())
        
        corpus.extend(device_descriptions)
        
        try:
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform(corpus)
            sim_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        except Exception:
            sim_scores = [0.1] * len(all_devices)

        results = []
        for idx, dev in enumerate(all_devices):
            specs = dev.specs
            category_name = dev.category_rel.name if dev.category_rel else ''
            base_score = float(sim_scores[idx]) * 40.0 # up to 40 pts from NLP text similarity
            reasons = []

            # Workload rule bonuses
            for wl_key in detected_workloads:
                rule = self.WORKLOAD_RULES[wl_key]
                if category_name in rule['preferred_categories']:
                    base_score += 25.0

                ram_val = self._parse_ram(specs.get('RAM', ''))
                if rule['min_ram'] > 0:
                    if ram_val >= rule['min_ram']:
                        base_score += 15.0
                        reasons.append(f"✓ {ram_val} GB RAM meets your {wl_key.replace('_', ' ').upper()} workload threshold")
                    else:
                        base_score -= 10.0

                if rule['require_gpu']:
                    has_gpu = bool(specs.get('GPU') and 'integrated' not in specs.get('GPU', '').lower() and 'none' not in specs.get('GPU', '').lower())
                    if has_gpu:
                        base_score += 20.0
                        reasons.append(f"✓ Dedicated GPU ({specs.get('GPU')}) supports GPU acceleration")
                    else:
                        base_score -= 15.0

                # Append rule explanatory reasons
                for r in rule['reasons'][:2]:
                    if r not in reasons:
                        reasons.append(f"✓ {r}")

            # Availability bonus
            if dev.status == 'available':
                base_score += 15.0
                reasons.append("✓ Device is currently in stock & ready for immediate issue")
            else:
                base_score -= 25.0

            # Budget adherence
            if budget_limit:
                if dev.price_per_day <= budget_limit:
                    base_score += 15.0
                    reasons.append(f"✓ ₹{dev.price_per_day:.0f}/day fits within your ₹{budget_limit:.0f} target budget")
                else:
                    base_score -= 20.0

            # Normalize match score between 35% and 98%
            normalized_score = max(35, min(98, int(base_score + 25)))

            if not reasons:
                reasons.append(f"✓ Compatible specifications for campus project work")
                reasons.append(f"✓ Affordable student rental rate at ₹{dev.price_per_day:.0f}/day")

            total_est = dev.price_per_day * rental_days

            results.append({
                'device': dev,
                'match_score': normalized_score,
                'reasons': reasons[:4],
                'rental_days': rental_days,
                'estimated_total': total_est,
                'status': dev.status
            })

        # Sort by match score descending
        results.sort(key=lambda x: (x['status'] == 'available', x['match_score']), reverse=True)
        return results[:top_k]

    @staticmethod
    def _parse_ram(ram_str):
        if not ram_str:
            return 0
        match = re.search(r'(\d+)', str(ram_str))
        return int(match.group(1)) if match else 0
