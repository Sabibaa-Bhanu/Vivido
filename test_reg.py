##from backend.user_management import register_user, forgot_password
##
## Valid registration
##print(register_user("alice", "alice@example.com", "StrongPass1!"))
##
## Invalid email
##print(register_user("bob", "bobexample.com", "StrongPass1!"))
##
## Weak password
##print(register_user("charlie", "charlie@example.com", "weak"))
##
## Duplicate email
##print(register_user("alice2", "alice@example.com", "StrongPass1!"))
##
## Forgot password
##print(forgot_password("alice@example.com"))
##print(forgot_password("nonexistent@example.com"))
##
##def test_invalid_email():
##    assert register_user("user1", "bademail", "Strong@123")["success"] is False
##
##def test_weak_password():
##    assert register_user("user2", "user2@mail.com", "123")["success"] is False
##
##def test_successful_registration():
##    assert register_user("user3", "user3@mail.com", "Strong@123")["success"] is True
##

from backend.user_management import register_user

def print_result(test_name, result):
    status = "PASSED" if result else "FAILED"
    print(f"{test_name}: {status}")


# 1️⃣ Invalid email format
def test_invalid_email():
    response = register_user(
        username="testuser1",
        email="invalidemail",
        password="Strong@123"
    )
    return not response["success"]


# 2️⃣ Weak password (too short)
def test_weak_password():
    response = register_user(
        username="testuser2",
        email="test2@gmail.com",
        password="abc"
    )
    return not response["success"]


# 3️⃣ Password without uppercase
def test_password_no_uppercase():
    response = register_user(
        username="testuser3",
        email="test3@gmail.com",
        password="strong@123"
    )
    return not response["success"]


# 4️⃣ Password without special character
def test_password_no_special_char():
    response = register_user(
        username="testuser4",
        email="test4@gmail.com",
        password="Strong123"
    )
    return not response["success"]


# 5️⃣ Successful registration
def test_successful_registration():
    response = register_user(
        username="validuser",
        email="validuser@gmail.com",
        password="Strong@123"
    )
    return response["success"]


# 6️⃣ Duplicate username
def test_duplicate_username():
    register_user(
        username="duplicateuser",
        email="dup1@gmail.com",
        password="Strong@123"
    )

    response = register_user(
        username="duplicateuser",
        email="dup2@gmail.com",
        password="Strong@123"
    )
    return not response["success"]


# 7️⃣ Duplicate email
def test_duplicate_email():
    register_user(
        username="emailuser1",
        email="duplicate@gmail.com",
        password="Strong@123"
    )

    response = register_user(
        username="emailuser2",
        email="duplicate@gmail.com",
        password="Strong@123"
    )
    return not response["success"]


# ▶️ Run all tests
if __name__ == "__main__":
    print_result("Invalid Email Test", test_invalid_email())
    print_result("Weak Password Test", test_weak_password())
    print_result("No Uppercase Password Test", test_password_no_uppercase())
    print_result("No Special Character Test", test_password_no_special_char())
    print_result("Successful Registration Test", test_successful_registration())
    print_result("Duplicate Username Test", test_duplicate_username())
    print_result("Duplicate Email Test", test_duplicate_email())
