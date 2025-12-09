from app.models.mongo_models import Certificate, StudentData, User
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StudentDataService:
    """Service to query student-specific data from MongoDB."""
    
    @staticmethod
    async def get_student_certificates(
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        user_role: str = "USER",
        organization_id: str = None
    ) -> List[Dict]:
        """Get certificates based on user role, matching by email or user ID."""
        try:
            # Query MongoDB certificates collection directly using Motor
            from motor.motor_asyncio import AsyncIOMotorClient
            from app.core.config import settings
            from bson import ObjectId
            from bson.errors import InvalidId
            
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            db = client[settings.MONGODB_DB_NAME]
            
            # Build query based on role
            if user_role == "MOE":
                # MOE: Get ALL certificates across all institutions
                query = {}
                limit = 10000
            elif user_role in ["ADMIN", "INSTITUTION"] and organization_id:
                # Admin/Institution: Get all certificates from their institution
                query = {"institutionId": ObjectId(organization_id)}
                limit = 1000
            else:
                # Student: Try multiple identifiers (email and user_id variants)
                or_filters = []

                if user_email:
                    or_filters.extend([
                        {"student.email": user_email},
                        {"studentEmail": user_email},
                        {"studentEmailId": user_email},
                    ])

                if user_id:
                    # Match both string and ObjectId representations
                    or_filters.append({"student_id": user_id})
                    or_filters.append({"studentId": user_id})
                    try:
                        object_id = ObjectId(user_id)
                        or_filters.append({"student_id": object_id})
                        or_filters.append({"studentId": object_id})
                    except (InvalidId, TypeError):
                        pass

                # Fallback to empty query if nothing to match
                query = {"$or": or_filters} if or_filters else {}
                limit = 200
            
            certificates_cursor = db.certificates.find(query)
            certificates = await certificates_cursor.to_list(length=limit)
            
            client.close()
            
            results = []
            for cert in certificates:
                issued_at = cert.get("issuedAt") or cert.get("issue_date")
                if hasattr(issued_at, "strftime"):
                    issued_at_str = issued_at.strftime("%Y-%m-%d")
                else:
                    issued_at_str = str(issued_at) if issued_at else "N/A"

                # Extract student information
                student_info = cert.get("student", {})
                
                results.append({
                    "certificate_id": cert.get("certificateId") or cert.get("certificate_id"),
                    "name": student_info.get("fullName") if student_info else cert.get("student_name"),
                    "father_name": student_info.get("fatherName"),
                    "course": student_info.get("course") if student_info else cert.get("course_name"),
                    "issue_date": issued_at_str,
                    "grade": student_info.get("cgpa") if student_info else cert.get("grade"),
                    "status": cert.get("status"),
                    "pdf_url": cert.get("pdfUrl") or cert.get("storage", {}).get("url"),
                    "cloudinary_url": cert.get("pdfUrl") or cert.get("storage", {}).get("url"),
                    "verification_url": cert.get("verificationUrl"),
                    "department": student_info.get("department") if student_info else cert.get("department"),
                    "roll_number": student_info.get("rollNumber") if student_info else cert.get("roll_number"),
                    "registration_number": student_info.get("registrationNumber"),
                    "passing_year": student_info.get("passingYear"),
                    "student_email": student_info.get("email") if student_info else cert.get("student_email"),
                    "blockchain_status": cert.get("blockchainStatus"),
                    "institution_name": cert.get("metadata", {}).get("institutionName")
                })

            return results
        except Exception as e:
            logger.error(f"Error fetching certificates: {e}")
            return []
    
    @staticmethod
    async def get_student_data(student_id: str) -> Optional[Dict]:
        """Get student data from MongoDB."""
        try:
            student = await StudentData.find_one({"student_id": student_id})
            if student:
                return {
                    "enrollment_number": student.enrollment_number,
                    "courses_enrolled": student.courses_enrolled,
                    "certificates_earned": student.certificates_earned,
                    "total_credits": student.total_credits,
                    "current_semester": student.current_semester,
                    "department": student.department,
                    "additional_info": student.additional_info
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching student data: {e}")
            return None
    
    @staticmethod
    async def get_student_summary(
        user_email: str,
        user_name: str,
        user_role: str = "USER",
        organization_id: str = None,
        user_id: Optional[str] = None
    ) -> str:
        """Get a formatted summary based on user role."""
        try:
            # Get certificates based on role
            certificates = await StudentDataService.get_student_certificates(
                user_email=user_email,
                user_id=user_id,
                user_role=user_role,
                organization_id=organization_id
            )
            cert_count = len(certificates)
            
            # Get student data (optional - for future use)
            student_data = None  # Not using student_id anymore
            
            # Format summary based on role
            if user_role == "MOE":
                summary = f"Ministry of Education - System Overview for {user_name}:\n\n"
                summary += f"Role: Ministry of Education (MOE)\n"
                summary += f"Total Certificates in System: {cert_count}\n"
                
                if certificates:
                    summary += "\nRecent Certificates (showing up to 15):\n"
                    for i, cert in enumerate(certificates[:15], 1):
                        summary += f"{i}. {cert['name']} ({cert.get('student_email', 'N/A')}) - {cert['course']} "
                        summary += f"(Issued: {cert['issue_date']}, Status: {cert['status']})\n"
                    
                    if cert_count > 15:
                        summary += f"\n...and {cert_count - 15} more certificates across all institutions.\n"
            elif user_role in ["ADMIN", "INSTITUTION"]:
                summary = f"Institution Admin Profile for {user_name}:\n\n"
                summary += f"Role: {user_role}\n"
                summary += f"Total Certificates Issued: {cert_count}\n"
                
                if certificates:
                    summary += "\nRecent Certificates (showing up to 10):\n"
                    for i, cert in enumerate(certificates[:10], 1):
                        summary += f"{i}. {cert['name']} ({cert.get('student_email', 'N/A')}) - {cert['course']} "
                        summary += f"(Issued: {cert['issue_date']}, Status: {cert['status']})\n"
                    
                    if cert_count > 10:
                        summary += f"\n...and {cert_count - 10} more certificates.\n"
            else:
                # Student profile
                summary = f"Student Profile for {user_name}:\n\n"
                
                if student_data:
                    summary += f"Enrollment Number: {student_data['enrollment_number']}\n"
                    summary += f"Department: {student_data.get('department', 'N/A')}\n"
                    summary += f"Current Semester: {student_data.get('current_semester', 'N/A')}\n"
                    summary += f"Total Credits: {student_data.get('total_credits', 0)}\n"
                    summary += f"Courses Enrolled: {len(student_data.get('courses_enrolled', []))}\n"
                
                summary += f"\nCertificates Issued: {cert_count}\n"
                
                if certificates:
                    summary += "\nCertificate Details:\n"
                    for i, cert in enumerate(certificates, 1):
                        summary += f"\n{i}. {cert['name']} - {cert['course']}\n"
                        summary += f"   Certificate ID: {cert['certificate_id']}\n"
                        summary += f"   Issued: {cert['issue_date']}, Status: {cert['status']}\n"
                        summary += f"   Grade/CGPA: {cert.get('grade', 'N/A')}\n"
                        if cert.get('cloudinary_url'):
                            summary += f"   📄 PDF Download: {cert['cloudinary_url']}\n"
                        if cert.get('verification_url'):
                            summary += f"   🔗 Verify: {cert['verification_url']}\n"
            
            return summary
        except Exception as e:
            logger.error(f"Error creating student summary: {e}")
            return f"Error retrieving data for {user_name}"
