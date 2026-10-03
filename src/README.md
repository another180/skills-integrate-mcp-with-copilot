# Mergington High School Activities API

A simple FastAPI application that lets students view extracurricular activities
and lets authenticated teachers manage registrations.

## Features

- View all available extracurricular activities
- Sign up and unregister students as a teacher
- View activity rosters without signing in

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create a teacher account. The password is entered interactively and stored
   as a salted PBKDF2 hash in a local file that is excluded from version control:

   ```
   python src/create_teacher.py teacher
   ```

   Run the command again with another username to add another teacher.

3. Start the application from the repository root:

   ```
   uvicorn app:app --app-dir src --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

   Open the activities page at http://localhost:8000.

Teachers use **Teacher Login** in the page header. A teacher session expires
after eight hours or when the server restarts. Students can still view all
activities and rosters without signing in.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/session`                                                   | Check the current browser's teacher session                         |
| POST   | `/auth/login`                                                      | Sign in using a teacher username and password                       |
| POST   | `/auth/logout`                                                     | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student (teacher login required)                          |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher login required)                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and session data is stored in memory, which means registrations reset
and teacher sessions end when the server restarts. Teacher accounts are stored
separately in `src/teachers.json`; do not commit or share that file.
