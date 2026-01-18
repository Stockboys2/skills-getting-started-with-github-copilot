"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state between tests"""
    # Store original state
    from app import activities
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for name, activity in activities.items():
        activity["participants"] = original_activities[name]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns status code 200"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        assert isinstance(response.json(), dict)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that the response contains expected activities"""
        response = client.get("/activities")
        activities = response.json()
        expected_activities = [
            "Chess Club",
            "Basketball Team",
            "Soccer Club",
            "Art Club",
            "Drama Club",
            "Debate Team",
            "Math Club",
            "Programming Class",
            "Gym Class"
        ]
        for activity in expected_activities:
            assert activity in activities
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            for field in required_fields:
                assert field in activity_data, f"Activity {activity_name} missing field {field}"
    
    def test_participants_is_list(self, client):
        """Test that participants field is a list"""
        response = client.get("/activities")
        activities = response.json()
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_data["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=student@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_email(self, client, reset_activities):
        """Test signup with duplicate email returns 400"""
        # First signup
        response1 = client.post(
            "/activities/Basketball Team/signup?email=student@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Second signup with same email
        response2 = client.post(
            "/activities/Basketball Team/signup?email=student@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds participant to activity"""
        from app import activities
        
        initial_count = len(activities["Soccer Club"]["participants"])
        
        response = client.post(
            "/activities/Soccer Club/signup?email=newsoccer@mergington.edu"
        )
        assert response.status_code == 200
        
        updated_count = len(activities["Soccer Club"]["participants"])
        assert updated_count == initial_count + 1
        assert "newsoccer@mergington.edu" in activities["Soccer Club"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # First signup
        client.post(
            "/activities/Soccer Club/signup?email=student@mergington.edu"
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Soccer Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_nonexistent_participant(self, client, reset_activities):
        """Test unregister for non-existent participant returns 400"""
        response = client.delete(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes participant from activity"""
        from app import activities
        
        # First signup
        client.post(
            "/activities/Art Club/signup?email=newart@mergington.edu"
        )
        assert "newart@mergington.edu" in activities["Art Club"]["participants"]
        
        # Then unregister
        response = client.delete(
            "/activities/Art Club/unregister?email=newart@mergington.edu"
        )
        assert response.status_code == 200
        assert "newart@mergington.edu" not in activities["Art Club"]["participants"]
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        from app import activities
        
        # Chess Club has initial participants
        initial_participants = activities["Chess Club"]["participants"].copy()
        assert len(initial_participants) > 0
        
        email_to_remove = initial_participants[0]
        response = client.delete(
            f"/activities/Chess Club/unregister?email={email_to_remove}"
        )
        assert response.status_code == 200
        assert email_to_remove not in activities["Chess Club"]["participants"]


class TestIntegrationScenarios:
    """Integration tests for common user scenarios"""
    
    def test_signup_and_unregister_workflow(self, client, reset_activities):
        """Test complete workflow of signing up and then unregistering"""
        from app import activities
        
        email = "workflow@mergington.edu"
        activity = "Drama Club"
        
        # Initial state
        initial_count = len(activities[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        assert len(activities[activity]["participants"]) == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        assert len(activities[activity]["participants"]) == initial_count
    
    def test_cannot_register_twice(self, client, reset_activities):
        """Test that duplicate registration is prevented"""
        email = "duplicate@mergington.edu"
        activity = "Debate Team"
        
        # First signup
        response1 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response2.status_code == 400
    
    def test_multiple_students_signup(self, client, reset_activities):
        """Test multiple different students can sign up for same activity"""
        from app import activities
        
        activity = "Math Club"
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        initial_count = len(activities[activity]["participants"])
        
        for email in students:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        assert len(activities[activity]["participants"]) == initial_count + len(students)
        for email in students:
            assert email in activities[activity]["participants"]
