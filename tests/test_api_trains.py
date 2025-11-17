"""
Tests for train API endpoints.
"""

# Fixtures are automatically loaded from conftest.py


def test_create_train(client):
    """Test creating a new train."""
    response = client.post(
        "/api/v1/trains",
        json={"code": "SM101", "description": "Express service"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "SM101"
    assert data["description"] == "Express service"
    assert "id" in data


def test_create_train_no_description(client):
    """Test creating a train without description."""
    response = client.post("/api/v1/trains", json={"code": "SM102"})
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "SM102"
    assert data["description"] is None


def test_create_train_duplicate_code(client):
    """Test that creating a train with duplicate code fails."""
    client.post("/api/v1/trains", json={"code": "SM101"})
    
    response = client.post("/api/v1/trains", json={"code": "SM101"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_train_invalid_data(client):
    """Test that invalid train data is rejected."""
    response = client.post("/api/v1/trains", json={"code": ""})
    assert response.status_code == 422


def test_list_trains(client):
    """Test listing all trains."""
    client.post("/api/v1/trains", json={"code": "SM101", "description": "Express"})
    client.post("/api/v1/trains", json={"code": "SM102", "description": "Local"})
    client.post("/api/v1/trains", json={"code": "SM103"})
    
    response = client.get("/api/v1/trains")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_list_trains_pagination(client):
    """Test train list pagination."""
    for i in range(5):
        client.post("/api/v1/trains", json={"code": f"SM{i}"})
    
    response = client.get("/api/v1/trains?skip=0&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    response = client.get("/api/v1/trains?skip=3&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_train(client):
    """Test getting a specific train."""
    create_response = client.post(
        "/api/v1/trains",
        json={"code": "SM999", "description": "Test train"}
    )
    train_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/trains/{train_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == train_id
    assert data["code"] == "SM999"


def test_get_train_not_found(client):
    """Test getting a non-existent train."""
    response = client.get("/api/v1/trains/999")
    assert response.status_code == 404


def test_update_train(client):
    """Test updating a train."""
    create_response = client.post(
        "/api/v1/trains",
        json={"code": "OLD", "description": "Old description"}
    )
    train_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/trains/{train_id}",
        json={"code": "NEW", "description": "New description"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "NEW"
    assert data["description"] == "New description"


def test_update_train_partial(client):
    """Test partial update of a train."""
    create_response = client.post(
        "/api/v1/trains",
        json={"code": "SM100", "description": "Original"}
    )
    train_id = create_response.json()["id"]
    
    # Update only description
    response = client.put(
        f"/api/v1/trains/{train_id}",
        json={"description": "Updated description"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "SM100"  # Unchanged
    assert data["description"] == "Updated description"


def test_update_train_duplicate_code(client):
    """Test that updating to a duplicate code fails."""
    client.post("/api/v1/trains", json={"code": "SM101"})
    create_response = client.post("/api/v1/trains", json={"code": "SM102"})
    train_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/trains/{train_id}",
        json={"code": "SM101"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_update_train_not_found(client):
    """Test updating a non-existent train."""
    response = client.put(
        "/api/v1/trains/999",
        json={"code": "NEW"}
    )
    assert response.status_code == 404


def test_delete_train(client):
    """Test deleting a train."""
    create_response = client.post("/api/v1/trains", json={"code": "DELETE_ME"})
    train_id = create_response.json()["id"]
    
    response = client.delete(f"/api/v1/trains/{train_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/trains/{train_id}")
    assert get_response.status_code == 404


def test_delete_train_not_found(client):
    """Test deleting a non-existent train."""
    response = client.delete("/api/v1/trains/999")
    assert response.status_code == 404

