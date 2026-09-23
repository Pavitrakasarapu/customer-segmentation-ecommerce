import secrets
from datetime import datetime, timedelta
from models import db


class OTPVerification(db.Model):
    __tablename__ = "otp_verifications"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_code = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)

    @classmethod
    def generate_otp(cls, email: str, expiry_minutes: int = 5) -> "OTPVerification":
        """Generate a cryptographically secure 6-digit OTP"""
        # Invalidate any existing unused OTPs for this email
        cls.query.filter(cls.email == email, cls.is_used == False).update({"is_used": True})
        
        # 6-digit cryptographically secure random number
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        now = datetime.utcnow()
        expires = now + timedelta(minutes=expiry_minutes)
        
        record = cls(
            email=email,
            otp_code=code,
            created_at=now,
            expires_at=expires,
            attempts=0,
            is_used=False
        )
        db.session.add(record)
        db.session.commit()
        return record

    def verify(self, code: str, max_attempts: int = 5) -> tuple[bool, str]:
        """Verify code against this record, managing attempt limits and expiry"""
        if self.is_used:
            return False, "This OTP has already been used. Please request a new one."
        
        if datetime.utcnow() > self.expires_at:
            self.is_used = True
            db.session.commit()
            return False, "This OTP has expired. Please request a new one."
        
        if self.attempts >= max_attempts:
            self.is_used = True
            db.session.commit()
            return False, "Maximum verification attempts exceeded. Please request a new OTP."
        
        self.attempts += 1
        
        if secrets.compare_digest(self.otp_code.strip(), code.strip()):
            self.is_used = True
            db.session.commit()
            return True, "OTP verified successfully."
        
        db.session.commit()
        remaining = max_attempts - self.attempts
        return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

    def __repr__(self):
        return f"<OTPVerification email={self.email} used={self.is_used} attempts={self.attempts}>"
