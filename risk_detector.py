class StudentRiskDetector:
    """
    AI Fraud & Student Risk Detection System.
    Evaluates rental histories, return punctuality, damage incident frequency,
    and fine settlement rates to provide an objective reliability score and
    decision-support guidance for college administrators.
    """

    @classmethod
    def evaluate_student(cls, student_user):
        """
        Analyzes a student's full historical record.
        Returns risk scores, risk level, flagged status, and decision support advice.
        """
        # Fetch related records
        all_rentals = list(student_user.rentals)
        all_fines = list(student_user.fines)
        all_bookings = list(student_user.bookings)

        total_rentals = len(all_rentals)
        total_bookings = len(all_bookings)

        # Baseline metrics
        late_returns = 0
        damaged_devices = 0

        for r in all_rentals:
            if r.status == 'overdue':
                late_returns += 1
            elif r.returned_at and r.due_date:
                # check if return date > due date
                if r.returned_at.date() > r.due_date:
                    late_returns += 1

            if r.inspection and r.inspection.ai_damage_detected and r.inspection.damage_score > 20.0:
                damaged_devices += 1

        unpaid_fines = [f for f in all_fines if f.status == 'pending']
        unpaid_fines_count = len(unpaid_fines)
        unpaid_fines_amount = sum(f.amount for f in unpaid_fines)

        # Calculations
        late_ratio = (late_returns / total_rentals) if total_rentals > 0 else 0.0
        damage_ratio = (damaged_devices / total_rentals) if total_rentals > 0 else 0.0

        # Composite risk points calculation (0 to 100)
        risk_points = 0.0
        factors = []

        if total_rentals == 0:
            return {
                'student_id': student_user.id,
                'student_name': student_user.name,
                'email': student_user.email,
                'department': student_user.department or 'General',
                'total_rentals': 0,
                'late_returns': 0,
                'damaged_devices': 0,
                'unpaid_fines_count': unpaid_fines_count,
                'unpaid_fines_amount': unpaid_fines_amount,
                'reliability_score': 85.0, # Fresh neutral profile
                'risk_score': 15.0,
                'risk_level': 'Low Risk',
                'flagged': False,
                'factors': ['New account with no prior rental history (Standard student tier)'],
                'recommendation': 'Standard verification required on first equipment checkout.'
            }

        # 1. Late return penalty
        if late_ratio > 0.5:
            risk_points += 35.0
            factors.append(f"High late return rate: {int(late_ratio * 100)}% ({late_returns} of {total_rentals} rentals)")
        elif late_ratio > 0.2:
            risk_points += 18.0
            factors.append(f"Moderate late return frequency ({late_returns} late returns)")

        # 2. Damage incidents penalty
        if damaged_devices >= 3:
            risk_points += 40.0
            factors.append(f"Recurring equipment damage history ({damaged_devices} damaged device incidents)")
        elif damaged_devices >= 1:
            risk_points += 20.0
            factors.append(f"Recorded past device damage ({damaged_devices} incident)")

        # 3. Unpaid fines penalty
        if unpaid_fines_count >= 2:
            risk_points += 25.0
            factors.append(f"Multiple overdue fines (₹{unpaid_fines_amount:.0f} pending across {unpaid_fines_count} fines)")
        elif unpaid_fines_count == 1:
            risk_points += 12.0
            factors.append(f"Pending fine payment of ₹{unpaid_fines_amount:.0f}")

        # Scale final risk score
        risk_score = min(100.0, round(risk_points, 1))
        reliability_score = max(5.0, round(100.0 - risk_score, 1))

        # Risk Classification & Decision Support
        if risk_score >= 50.0:
            risk_level = 'High Risk'
            flagged = True
            recommendation = (
                f"FLAGGED FOR REVIEW: Recommend requiring staff manager interview, "
                f"settling ₹{unpaid_fines_amount:.0f} pending fines, and holding a ₹1,000 security deposit."
            )
        elif risk_score >= 25.0:
            risk_level = 'Medium Risk'
            flagged = False
            recommendation = (
                "MONITOR: Allow rental for standard equipment; prompt student about return deadlines."
            )
        else:
            risk_level = 'Low Risk'
            flagged = False
            factors.append("Consistently returns equipment punctually and in good condition")
            recommendation = "VERIFIED GOOD STANDING: Eligible for express auto-approval & premium devices."

        return {
            'student_id': student_user.id,
            'student_name': student_user.name,
            'email': student_user.email,
            'department': student_user.department or 'General',
            'total_rentals': total_rentals,
            'late_returns': late_returns,
            'damaged_devices': damaged_devices,
            'unpaid_fines_count': unpaid_fines_count,
            'unpaid_fines_amount': unpaid_fines_amount,
            'reliability_score': reliability_score,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'flagged': flagged,
            'factors': factors,
            'recommendation': recommendation
        }
