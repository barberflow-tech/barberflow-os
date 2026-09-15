import pytest


@pytest.mark.django_db
def test_admin_redirects_to_login(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")
