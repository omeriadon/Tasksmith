from datetime import date
from flask import Flask, request, render_template, g, redirect, url_for, jsonify, session #type: ignore
from dotenv import load_dotenv #type: ignore
import os
from supabase_client import supabase

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# Flask secret key - used for:
# - Session encryption and security
# - CSRF protection
# - Secure cookie signing
# - Flash messages encryption
# IMPORTANT: Should be a random, complex string in production!
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

def get_current_user():
    """Get current authenticated user from session"""
    try:
        # First, try to restore session from storage if needed
        current_session = supabase.auth.get_session()
        if not current_session or not current_session.access_token:
            print("No active session found, attempting to restore from storage...")
            
            # Try to get session from storage
            try:
                stored_session = supabase.auth.get_session()
                if stored_session and stored_session.access_token:
                    print("Session restored from storage")
                else:
                    print("No stored session available")
            except Exception as e:
                print(f"Error restoring session: {str(e)}")
        
        # Get user from current auth session
        user = supabase.auth.get_user()
        if user and user.user:
            print(f"Current user: {user.user.id}")
            return user.user
        else:
            print("No authenticated user found")
            return None
    except Exception as e:
        print(f"Error getting current user: {str(e)}")
        return None

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

# MARK: /
@app.route('/')
def index():
    """Main route - render template with user data if authenticated"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    user_name = user.user_metadata.get('username', user.email.split('@')[0]) if user else 'Guest'
    return render_template('index.html', name=user_name)

@app.route("/signin/github")
def signin_with_github():
    """Sign in with GitHub OAuth"""
    try:
        # Use the correct port (5524) for the redirect URL
        redirect_url = f"{request.scheme}://{request.host}/callback"
        print(f"Setting up GitHub OAuth with redirect URL: {redirect_url}")
        
        res = supabase.auth.sign_in_with_oauth({
            "provider": "github",
            "options": {
                "redirect_to": redirect_url
            },
        })
        return redirect(res.url)
    except Exception as e:
        print(f"GitHub OAuth error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'GitHub sign in error: {str(e)}'
        }), 500

@app.route("/callback")
def callback():
    """Handle OAuth callback"""
    print(f"=== CALLBACK DEBUG ===")
    print(f"Request URL: {request.url}")
    print(f"Request Host: {request.host}")
    print(f"Request Args: {dict(request.args)}")
    
    try:
        code = request.args.get("code")
        next_url = request.args.get("next", "/")
        
        print(f"OAuth callback received - Code: {code[:20] if code else 'None'}...")
        print(f"Next URL: {next_url}")

        if code:
            print("Exchanging code for session...")
            res = supabase.auth.exchange_code_for_session({"auth_code": code})
            
            if res.user:
                print(f"User authenticated: {res.user.email}")
                
                # Store user info in session for easy access
                session['user_id'] = res.user.id
                session['user_email'] = res.user.email
                session['authenticated'] = True
                
                # CRITICAL: Ensure the session is properly set for RLS
                print(f"Session after auth: {res.session}")
                if res.session:
                    print(f"Access token: {res.session.access_token[:50]}...")
                    
                    # Force set the session to ensure RLS works
                    supabase.auth.set_session(res.session.access_token, res.session.refresh_token)
                    print("Session explicitly set on supabase client")
                
                print("Redirecting to home page...")
                return redirect("/")
            else:
                print("No user returned from exchange")
                return redirect("/login?error=auth_failed")
        else:
            print("No authorization code received")
            return redirect("/login?error=no_code")
            
    except Exception as e:
        print(f"OAuth callback error: {str(e)}")
        return redirect("/login?error=auth_failed")

# Test route to verify callback URL
@app.route("/test-callback")
def test_callback():
    """Test route to verify the callback is working"""
    return f"""
    <h1>Callback Test</h1>
    <p>Your Flask app is running correctly on {request.host}</p>
    <p>Request URL: {request.url}</p>
    <p>If you can see this, the port and routing are working!</p>
    <a href="/login">Go to Login</a>
    """

# Debug route to check auth state
@app.route("/debug-auth")
def debug_auth():
    """Debug route to check authentication state"""
    try:
        # Check Flask session
        flask_session_data = {
            'user_id': session.get('user_id'),
            'user_email': session.get('user_email'),
            'authenticated': session.get('authenticated')
        }
        
        # Check Supabase auth
        supabase_user = supabase.auth.get_user()
        supabase_auth_data = {
            'user_exists': supabase_user.user is not None if supabase_user else False,
            'user_id': supabase_user.user.id if supabase_user and supabase_user.user else None,
            'user_email': supabase_user.user.email if supabase_user and supabase_user.user else None
        }
        
        # Check get_current_user function
        current_user = get_current_user()
        current_user_data = {
            'user_exists': current_user is not None,
            'user_id': current_user.id if current_user else None,
            'user_email': current_user.email if current_user else None
        }
        
        return f"""
        <h1>Authentication Debug</h1>
        <h2>Flask Session:</h2>
        <pre>{flask_session_data}</pre>
        
        <h2>Supabase Auth:</h2>
        <pre>{supabase_auth_data}</pre>
        
        <h2>get_current_user():</h2>
        <pre>{current_user_data}</pre>
        
        <a href="/courses">Go to Courses</a>
        <br><a href="/debug-rls">Test RLS Policies</a>
        """
        
    except Exception as e:
        return f"<h1>Debug Error</h1><p>{str(e)}</p>"

# Debug route to test RLS policies
@app.route("/debug-rls")
def debug_rls():
    """Debug route to test RLS policies"""
    try:
        current_user = get_current_user()
        if not current_user:
            return "<h1>Not authenticated</h1><a href='/login'>Login</a>"
        
        results = {}
        
        # Test 1: Can we SELECT from courses?
        try:
            courses_select = supabase.table('courses').select('*').execute()
            results['courses_select'] = {
                'success': True,
                'data': courses_select.data,
                'count': len(courses_select.data)
            }
        except Exception as e:
            results['courses_select'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 2: Can we SELECT from tasks?
        try:
            tasks_select = supabase.table('tasks').select('*').execute()
            results['tasks_select'] = {
                'success': True,
                'data': tasks_select.data,
                'count': len(tasks_select.data)
            }
        except Exception as e:
            results['tasks_select'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 3: Try a simple INSERT to courses with explicit user_id
        try:
            test_course = {
                'name': f'Test Course {current_user.id[:8]}',
                'description': 'Test course for RLS debugging',
                'user_id': current_user.id  # Explicit user_id, not relying on auth.uid()
            }
            
            courses_insert = supabase.table('courses').insert(test_course).execute()
            results['courses_insert'] = {
                'success': True,
                'data': courses_insert.data
            }
            
            # Clean up the test course
            if courses_insert.data:
                supabase.table('courses').delete().eq('id', courses_insert.data[0]['id']).execute()
                results['courses_insert']['cleaned_up'] = True
                
        except Exception as e:
            results['courses_insert'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 4: Check what auth.uid() returns from Flask app context
        try:
            # This won't work because we can't run raw SQL from supabase-py client
            # But we can check if our user context is properly set
            auth_check = supabase.auth.get_user()
            results['auth_context'] = {
                'user_authenticated': auth_check.user is not None,
                'user_id': auth_check.user.id if auth_check.user else None,
                'matches_current_user': auth_check.user.id == current_user.id if auth_check.user else False
            }
        except Exception as e:
            results['auth_context'] = {
                'success': False,
                'error': str(e)
            }
        
        return f"""
        <h1>RLS Policy Debug</h1>
        <h2>Current User: {current_user.email} (ID: {current_user.id})</h2>
        
        <h3>Test Results:</h3>
        <pre>{results}</pre>
        
        <h3>Key Finding:</h3>
        <p>auth.uid() returns NULL in SQL Editor because you're not authenticated there.</p>
        <p>RLS policy is now correct: {'{authenticated}'} role</p>
        <p>The issue was that auth.uid() needs to be called from an authenticated context (your Flask app).</p>
        
        <a href="/debug-auth">Back to Auth Debug</a>
        <br><a href="/test-course-creation">Test Course Creation</a>
        """
        
    except Exception as e:
        return f"<h1>RLS Debug Error</h1><p>{str(e)}</p>"

# Test route for course creation from authenticated context
@app.route("/test-course-creation")
def test_course_creation():
    """Test course creation from authenticated Flask context"""
    try:
        current_user = get_current_user()
        if not current_user:
            return "<h1>Not authenticated</h1><a href='/login'>Login</a>"
        
        results = {}
        
        # Test 1: Check session storage contents
        try:
            session_keys = list(session.keys())
            results['session_contents'] = {
                'keys': session_keys,
                'has_auth_data': any('supabase' in key.lower() or 'auth' in key.lower() for key in session_keys)
            }
        except Exception as e:
            results['session_contents'] = {'error': str(e)}
        
        # Test 2: Try to refresh/restore the session before course creation
        try:
            # Force refresh the auth session
            print("Attempting to refresh auth session...")
            auth_response = supabase.auth.get_session()
            print(f"Auth session: {auth_response}")
            
            results['session_refresh'] = {
                'success': True,
                'has_session': auth_response is not None,
                'session_data': str(auth_response)[:200] if auth_response else None
            }
        except Exception as e:
            results['session_refresh'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 3: Try course creation with explicit session management
        try:
            test_course = {
                'name': f'Flask Auth Test {current_user.id[:8]}',
                'description': 'Testing course creation from Flask authenticated context',
                'user_id': current_user.id
            }
            
            print(f"Testing course creation with data: {test_course}")
            
            # Try to ensure we have a valid auth session
            session_check = supabase.auth.get_user()
            print(f"Pre-insert session check: {session_check}")
            
            response = supabase.table('courses').insert(test_course).execute()
            
            results['course_creation'] = {
                'success': True,
                'data': response.data,
                'message': 'Course created successfully from Flask app!'
            }
            
            # Clean up
            if response.data:
                delete_response = supabase.table('courses').delete().eq('id', response.data[0]['id']).execute()
                results['cleanup'] = {
                    'success': True,
                    'message': 'Test course cleaned up'
                }
                
        except Exception as e:
            results['course_creation'] = {
                'success': False,
                'error': str(e),
                'message': 'Course creation failed from Flask app'
            }
        
        return f"""
        <h1>Course Creation Test (Enhanced)</h1>
        <h2>Testing from authenticated Flask context</h2>
        <h3>User: {current_user.email}</h3>
        
        <h3>Results:</h3>
        <pre>{results}</pre>
        
        <h3>Next Steps:</h3>
        <p>1. Run the RLS bypass test in SQL Editor to confirm RLS is the issue</p>
        <p>2. If RLS bypass works, we need to fix session handling</p>
        <p>3. The issue is likely that auth.uid() returns NULL during database operations</p>
        
        <a href="/debug-rls">Back to RLS Debug</a>
        <br><a href="/test-manual-session">Test Manual Session Restore</a>
        """
        
    except Exception as e:
        return f"<h1>Course Creation Test Error</h1><p>{str(e)}</p>"



# MARK: Courses
@app.route('/courses')
def courses():
    """Courses management page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('courses.html')

# MARK: Tasks
@app.route('/tasks')
def tasks():
    """Tasks management page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('tasks.html')

# MARK: api/Courses
@app.route('/api/courses', methods=['GET', 'POST'])
@require_auth
def manage_courses():
    """Get all courses or create a new course"""
    if request.method == 'GET':
        try:
            # RLS Policy: Only returns courses where user_id = auth.uid()
            # This automatically enforces security - users only see their own courses
            response = supabase.table('courses').select('*').execute()
            return jsonify({
                'status': 'success',
                'courses': response.data
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error fetching courses: {str(e)}'
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            course_name = data.get('courseName')
            description = data.get('description', '')
            
            if not course_name:
                return jsonify({
                    'status': 'error',
                    'message': 'Course name is required'
                }), 400
            
            # Get current user ID for RLS
            current_user = get_current_user()
            if not current_user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not authenticated'
                }), 401
            
            print(f"Creating course for user: {current_user.id}")
            print(f"User ID type: {type(current_user.id)}")
            print(f"Course data: {course_name}, {description}")
            
            # Debug: Check if supabase client is authenticated
            try:
                auth_user = supabase.auth.get_user()
                if auth_user and auth_user.user:
                    print(f"Supabase client authenticated as: {auth_user.user.id}")
                    print(f"Supabase user ID type: {type(auth_user.user.id)}")
                    print(f"User IDs match: {current_user.id == auth_user.user.id}")
                else:
                    print("ERROR: Supabase client not authenticated!")
                    
                # Test the RLS policy directly
                print("Testing RLS policy with SELECT query...")
                test_select = supabase.table('courses').select('*').execute()
                print(f"SELECT query result: {test_select.data}")
                
            except Exception as e:
                print(f"Error checking supabase auth: {str(e)}")
            
            course_data = {
                'name': course_name,
                'description': description,
                'user_id': current_user.id  # Use string, not converting to int
            }
            
            print(f"Inserting course data: {course_data}")
            print(f"user_id in course_data type: {type(course_data['user_id'])}")
            
            print(f"Inserting course data: {course_data}")
            
            # RLS Policy: user_id = auth.uid() check ensures this works
            response = supabase.table('courses').insert(course_data).execute()
            
            print(f"Supabase response: {response}")
            
            if response.data:
                created_course = response.data[0]
                return jsonify({
                    'status': 'success',
                    'message': 'Course created successfully',
                    'course': created_course
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to create course - no data returned'
                }), 400
                
        except Exception as e:
            error_msg = str(e)
            print(f"Course creation error: {error_msg}")
            return jsonify({
                'status': 'error',
                'message': f'Error creating course: {error_msg}'
            }), 500

# MARK: api/Courses/<course_id>
@app.route('/api/courses/<course_id>', methods=['PUT', 'DELETE'])
@require_auth
def modify_course(course_id):
    """Update or delete a course"""
    if request.method == 'PUT':
        try:
            data = request.get_json()
            response = supabase.table('courses').update(data).eq('id', course_id).execute()
            
            return jsonify({
                'status': 'success',
                'message': 'Course updated successfully',
                'course': response.data
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error updating course: {str(e)}'
            }), 500
    
    elif request.method == 'DELETE':
        try:
            response = supabase.table('courses').delete().eq('id', course_id).execute()
            
            return jsonify({
                'status': 'success',
                'message': 'Course deleted successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error deleting course: {str(e)}'
            }), 500

# MARK: api/Tasks
@app.route('/api/tasks', methods=['GET', 'POST'])
@require_auth
def manage_tasks():
    """Get all tasks or create a new task"""
    if request.method == 'GET':
        try:
            # RLS Policy: Only returns tasks where the user owns the course
            # Your policy checks: EXISTS(SELECT 1 FROM courses WHERE courses.id = tasks.course_id AND courses.user_id = auth.uid())
            
            # Simple query first - just get tasks without join
            response = supabase.table('tasks').select('*').execute()
            
            # If you want course names, do a separate query
            if response.data:
                for task in response.data:
                    course_response = supabase.table('courses').select('name').eq('id', task['course_id']).execute()
                    if course_response.data:
                        task['course_name'] = course_response.data[0]['name']
                    else:
                        task['course_name'] = 'Unknown Course'
            
            return jsonify({
                'status': 'success',
                'tasks': response.data
            })
        except Exception as e:
            print(f"Tasks fetch error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Error fetching tasks: {str(e)}'
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            task_title = data.get('taskTitle')
            notes = data.get('notes', '')
            course_id = data.get('courseId')
            due_date = data.get('dueDate')
            priority = data.get('priority', 'medium')
            completed = data.get('completed', "Not Started")
            
            if not task_title:
                return jsonify({
                    'status': 'error',
                    'message': 'Task title is required'
                }), 400
            
            if not course_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Course assignment is required'
                }), 400
            
            # Validate that the user owns the course (extra security check)
            current_user = get_current_user()
            if not current_user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not authenticated'
                }), 401
                
            # Check if user owns the course before creating task
            course_check = supabase.table('courses').select('id').eq('id', course_id).eq('user_id', current_user.id).execute()
            if not course_check.data:
                return jsonify({
                    'status': 'error',
                    'message': 'You can only create tasks for your own courses'
                }), 403
            
            if not due_date:
                # Default to tomorrow if not provided
                tomorrow = date.fromordinal(date.today().toordinal() + 1)
                due_date = tomorrow.isoformat()
            
            task_data = {
                'title': task_title,
                'notes': notes,
                'course_id': int(course_id),
                'due_date': due_date if due_date else None,
                'priority': priority,
                'completed': completed
            }
            
            # RLS Policy will ensure user can only create tasks for courses they own
            response = supabase.table('tasks').insert(task_data).execute()
            
            if response.data:
                created_task = response.data[0]
                return jsonify({
                    'status': 'success',
                    'message': 'Task created successfully',
                    'task': created_task
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to create task'
                }), 400
                
        except Exception as e:
            error_msg = str(e)
            return jsonify({
                'status': 'error',
                'message': f'Error creating task: {error_msg}'
            }), 500

# MARK: api/Tasks/<task_id>
@app.route('/api/tasks/<task_id>', methods=['PUT', 'DELETE'])
@require_auth
def modify_task(task_id):
    """Update or delete a task"""
    if request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Validate task exists first
            task_check = supabase.table('tasks').select('*').eq('id', task_id).execute()
            if not task_check.data:
                return jsonify({
                    'status': 'error',
                    'message': 'Task not found'
                }), 404
            
            # Prepare update data
            update_data = {}
            
            # Handle different update scenarios
            if 'completed' in data:
                update_data['completed'] = bool(data['completed'])
            
            if 'title' in data:
                update_data['title'] = data['title']
            
            if 'description' in data:
                update_data['description'] = data['description']
            
            if 'priority' in data and data['priority'] in ['low', 'medium', 'high']:
                update_data['priority'] = data['priority']
            
            if 'due_date' in data:
                update_data['due_date'] = data['due_date']
            
            if not update_data:
                return jsonify({
                    'status': 'error',
                    'message': 'No valid fields to update'
                }), 400
            
            # Add updated timestamp
            update_data['updated_at'] = 'now()'
            
            response = supabase.table('tasks').update(update_data).eq('id', task_id).execute()
            
            if response.data:
                return jsonify({
                    'status': 'success',
                    'message': 'Task updated successfully',
                    'task': response.data[0]
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to update task'
                }), 400
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error updating task: {str(e)}'
            }), 500
    
    elif request.method == 'DELETE':
        try:
            response = supabase.table('tasks').delete().eq('id', task_id).execute()
            
            return jsonify({
                'status': 'success',
                'message': 'Task deleted successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error deleting task: {str(e)}'
            }), 500

# MARK: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if request.method == 'GET':
        return render_template('login.html')
    
    elif request.method == 'POST':
        try:
            email = request.json.get('email')
            password = request.json.get('password')
            
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                session['user_id'] = response.user.id
                session['user_email'] = response.user.email
                session['authenticated'] = True
                
                return jsonify({
                    'status': 'success',
                    'message': 'Login successful',
                    'user': {
                        'id': response.user.id,
                        'email': response.user.email
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Login failed'
                }), 401
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Login error: {str(e)}'
            }), 500

# MARK: Logout
@app.route('/logout', methods=['POST'])
def logout():
    """Logout and clear session"""
    try:
        supabase.auth.sign_out()
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Logout successful'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Logout error: {str(e)}'
        }), 500

# MARK: Auth Status
@app.route('/api/auth/status')
def auth_status():
    """Check authentication status"""
    try:
        user = get_current_user()
        if user:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.user_metadata.get('username', user.email.split('@')[0])
                }
            })
        else:
            return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'authenticated': False, 'error': str(e)})

if __name__ == '__main__':
    # Check required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please check your .env file and add Supabase credentials")
        exit(1)
    
    print("Environment variables loaded successfully")
    print(f"Connecting to Supabase: {os.getenv('SUPABASE_URL')}")
    print("Flask app ready with Supabase integration!")
    
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true', 
        host='0.0.0.0', 
        port=5524
    )




