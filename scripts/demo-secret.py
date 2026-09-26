import secrets
import string

if __name__ == "__main__":
    # Runtime only. Redirect to a temporary file, never a tracked path.
    print(
        "DEMOSECRET_"
        + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(24))
    )
