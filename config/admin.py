from django.contrib import admin


class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)

        # Define your desired order of models
        desired_order = {
            "Companies": [
                "company",
                "companybranch",
                "car",
                "driver",
                "caroperation",
                "companycashrequest",
            ],
            "Users": [
                "user",
                "companyuser",
                "firebase_token",
                "stationowner",
                "stationbranchmanager",
                "worker",
            ],
        }
        # Reorder the app_list
        for app in app_list:
            if app["name"] in desired_order:
                app["models"].sort(
                    key=lambda x: desired_order[app["name"]].index(
                        x["object_name"].lower()
                    )
                )
        return app_list


# Replace the default admin site
custom_admin_site = CustomAdminSite(name="custom_admin")
