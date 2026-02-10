from django.urls import path
from webui import views

app_name = "webui"

urlpatterns = [
    path("", views.create_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("create/", views.create_view, name="create"),
    path("update/", views.update_view, name="update"),
    path("delete/", views.delete_view, name="delete"),
    path("view/", views.view_view, name="view"),
    path("warehouse/", views.warehouse_view, name="warehouse"),
    path("bulk-update/", views.bulk_update_view, name="bulk_update"),
    path("api/subcategories/", views.subcategories_view, name="subcategories"),
]
