from fastapi import APIRouter
from app.candidate.router import router as candidate_router
from app.career_profiles.router import router as career_profiles_router
from app.jobs.router import router as jobs_router
from app.extraction.router import router as extraction_router
from app.matching.router import router as matching_router
from app.resumes.router import router as resumes_router

api_v1_router = APIRouter(prefix="/v1")

# Mount Domain Routers
api_v1_router.include_router(candidate_router, prefix="/candidate", tags=["Candidate"])
api_v1_router.include_router(career_profiles_router, prefix="/career-profiles", tags=["Career Profiles"])
api_v1_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_v1_router.include_router(extraction_router, prefix="/extraction", tags=["Job Understanding & Skill Extraction"])
api_v1_router.include_router(matching_router, prefix="/matching", tags=["Matching Engine"])
api_v1_router.include_router(resumes_router, prefix="/resumes", tags=["Resume Tailoring & Intelligence"])
# api_v1_router.include_router(applications_router, prefix="/applications", tags=["Applications"])
