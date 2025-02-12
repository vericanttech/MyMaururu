import sqlite3
import bcrypt
import getpass
import sys


def create_admin():
    print("Create Admin User")
    print("-----------------")

    # Get username and password
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        sys.exit(1)

    password = getpass.getpass("Enter password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if password != confirm_password:
        print("Error: Passwords don't match")
        sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long")
        sys.exit(1)

    # Hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    try:
        # Connect to database
        conn = sqlite3.connect('store.db')
        c = conn.cursor()

        # Check if user already exists
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        if c.fetchone() is not None:
            print("Error: Username already exists")
            sys.exit(1)

        # Create user
        c.execute('''
            INSERT INTO users (username, password, is_admin)
            VALUES (?, ?, ?)
        ''', (username, hashed_password, True))

        conn.commit()
        print("\nAdmin user created successfully!")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    create_admin()