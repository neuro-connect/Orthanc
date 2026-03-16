# Orthanc

# Warning

Before you use it in production make sure to update all hardcoded passwords and secret keys (search for `change-me`) in the `template_orthanc.json`. The used config must be named `orthanc.json`


# Keycloak setup

You can connect to keycloak at [http://localhost/keycloak](http://localhost/keycloak) with `admin` (pwd:`change-me`) user. Once connected, create a new admin user (in the `master` realms) and delete the `admin` user for security purpose.

## Add a new orthanc user

To add a new orthanc user, select the `orthanc` realm in the `Manage reals` tab, then go in `Users` tab and click on `Add user`. Once created, click on the user and go in the `Role Mapping`. Click on `Assign role`, change the filter for `Filter by realm roles` and select the role you want for the user. The permissions for each roles are defined in the `permissions.jsonc`.

# Orthanc

You can connect to orthanc at [http://localhost/orthanc/ui/app/](http://localhost/orthanc/ui/app/) with your credentials.
