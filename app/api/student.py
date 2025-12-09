from fastapi import APIRouter, HTTPException, Depends
from app.models.mongo_models import User, Certificate, StudentData
from app.api.auth_mongo import get_current_user_mongo
from app.services.student_service import StudentDataService
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/student", tags=["Student Data"])


class CertificateCreate(BaseModel):
    certificate_name: str
    course_name: str
    certificate_id: str
    grade: Optional[str] = None
    issue_date: Optional[datetime] = None


class StudentDataCreate(BaseModel):
    enrollment_number: str
    courses_enrolled: List[str] = []
    current_semester: Optional[int] = None
    department: Optional[str] = None


@router.get("/my-certificates")
async def get_my_certificates(current_user: User = Depends(get_current_user_mongo)):
    """Get all certificates for the logged-in student."""
    certificates = await StudentDataService.get_student_certificates(
        user_email=current_user.email,
        user_id=str(current_user.id)
    )
    return {
        "student_name": current_user.full_name,
        "total_certificates": len(certificates),
        "certificates": certificates
    }


@router.get("/my-profile")
async def get_my_student_profile(current_user: User = Depends(get_current_user_mongo)):
    """Get complete student profile with certificates and data."""
    student_data = await StudentDataService.get_student_data(str(current_user.id))
    certificates = await StudentDataService.get_student_certificates(
        user_email=current_user.email,
        user_id=str(current_user.id)
    )
    
    return {
        "student_name": current_user.full_name,
        "email": current_user.email,
        "student_data": student_data,
        "certificates": {
            "total": len(certificates),
            "list": certificates
        }
    }


@router.post("/add-certificate")
async def add_certificate(
    cert_data: CertificateCreate,
    current_user: User = Depends(get_current_user_mongo)
):
    """Add a certificate for the current student."""
    certificate = Certificate(
        student_id=str(current_user.id),
        certificate_name=cert_data.certificate_name,
        course_name=cert_data.course_name,
        certificate_id=cert_data.certificate_id,
        grade=cert_data.grade,
        issue_date=cert_data.issue_date or datetime.utcnow(),
        status="issued"
    )
    
    await certificate.insert()
    
    # Update certificate count in student data
    student_data = await StudentData.find_one({"student_id": str(current_user.id)})
    if student_data:
        student_data.certificates_earned += 1
        await student_data.save()
    
    return {
        "message": "Certificate added successfully",
        "certificate_id": cert_data.certificate_id
    }


@router.post("/setup-profile")
async def setup_student_profile(
    profile_data: StudentDataCreate,
    current_user: User = Depends(get_current_user_mongo)
):
    """Setup or update student profile data."""
    # Check if profile exists
    existing = await StudentData.find_one({"student_id": str(current_user.id)})
    
    if existing:
        # Update existing
        existing.enrollment_number = profile_data.enrollment_number
        existing.courses_enrolled = profile_data.courses_enrolled
        existing.current_semester = profile_data.current_semester
        existing.department = profile_data.department
        await existing.save()
        message = "Profile updated successfully"
    else:
        # Create new
        student_data = StudentData(
            student_id=str(current_user.id),
            enrollment_number=profile_data.enrollment_number,
            courses_enrolled=profile_data.courses_enrolled,
            current_semester=profile_data.current_semester,
            department=profile_data.department,
            certificates_earned=0
        )
        await student_data.insert()
        message = "Profile created successfully"
    
    return {"message": message}
