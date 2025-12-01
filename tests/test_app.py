import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities(self):
        """Test that we can retrieve all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
        
        # Verify activity structure
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self):
        """Test successful signup"""
        email = "test@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "message" in result
        assert email in result["message"]
        assert activity_name in result["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities[activity_name]["participants"]

    def test_signup_already_registered(self):
        """Test signup fails when student is already registered"""
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"  # Already in participants
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={existing_email}"
        )
        assert response.status_code == 400
        
        result = response.json()
        assert "already signed up" in result["detail"]

    def test_signup_nonexistent_activity(self):
        """Test signup fails for non-existent activity"""
        email = "test@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert response.status_code == 404
        
        result = response.json()
        assert "Activity not found" in result["detail"]

    def test_signup_multiple_activities(self):
        """Test that a student can signup for multiple activities"""
        email = "multiactivity@mergington.edu"
        
        # Sign up for first activity
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(
            f"/activities/Programming Class/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify in both activities
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self):
        """Test successful unregister"""
        email = "test-unregister@mergington.edu"
        activity_name = "Tennis Club"
        
        # First sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Verify signup worked
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity_name]["participants"]
        
        # Now unregister
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "Unregistered" in result["message"]
        assert email in result["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        assert email not in activities_response.json()[activity_name]["participants"]

    def test_unregister_not_registered(self):
        """Test unregister fails when student is not registered"""
        email = "notregistered@mergington.edu"
        activity_name = "Drama Club"
        
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert response.status_code == 400
        
        result = response.json()
        assert "not found" in result["detail"]

    def test_unregister_nonexistent_activity(self):
        """Test unregister fails for non-existent activity"""
        email = "test@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert response.status_code == 404
        
        result = response.json()
        assert "Activity not found" in result["detail"]


class TestRootEndpoint:
    """Tests for the root / endpoint"""

    def test_root_redirect(self):
        """Test that root endpoint redirects to static files"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "static/index.html" in response.headers["location"]


class TestActivityAvailability:
    """Tests for activity availability logic"""

    def test_activity_spots_calculation(self):
        """Test that spots available is calculated correctly"""
        activities_response = client.get("/activities")
        activities = activities_response.json()
        
        for activity_name, activity_data in activities.items():
            max_participants = activity_data["max_participants"]
            current_participants = len(activity_data["participants"])
            
            # Verify current participants don't exceed max
            assert current_participants <= max_participants
