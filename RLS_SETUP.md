# Supabase RLS Setup Instructions

After implementing Supabase Auth and RLS (Row Level Security), you need to set up proper policies in your Supabase dashboard.

## Required RLS Policies

### 1. For `auth.users` table (built-in)

This is automatically managed by Supabase Auth.

### 2. For custom `users` table (if you have one)

```sql
-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view all users (for user management)
CREATE POLICY "Users can view all users" ON public.users
FOR SELECT USING (true);

-- Policy: Authenticated users can insert users
CREATE POLICY "Authenticated users can insert users" ON public.users
FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Policy: Users can update their own data
CREATE POLICY "Users can update own data" ON public.users
FOR UPDATE USING (auth.uid() = id);

-- Policy: Only service role can delete users
CREATE POLICY "Service role can delete users" ON public.users
FOR DELETE USING (auth.role() = 'service_role');
```

### 3. For `courses` table

```sql
-- Enable RLS
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view all courses
CREATE POLICY "Users can view all courses" ON public.courses
FOR SELECT USING (auth.role() = 'authenticated');

-- Policy: Users can insert courses
CREATE POLICY "Users can insert courses" ON public.courses
FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Policy: Users can update their own courses
CREATE POLICY "Users can update own courses" ON public.courses
FOR UPDATE USING (auth.uid() = user_id);

-- Policy: Users can delete their own courses
CREATE POLICY "Users can delete own courses" ON public.courses
FOR DELETE USING (auth.uid() = user_id);
```

### 4. For `tasks` table

```sql
-- Enable RLS
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view tasks for their courses
CREATE POLICY "Users can view tasks for their courses" ON public.tasks
FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.courses
    WHERE courses.id = tasks.course_id
    AND courses.user_id = auth.uid()
  )
);

-- Policy: Users can insert tasks for their courses
CREATE POLICY "Users can insert tasks for their courses" ON public.tasks
FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.courses
    WHERE courses.id = tasks.course_id
    AND courses.user_id = auth.uid()
  )
);

-- Policy: Users can update tasks for their courses
CREATE POLICY "Users can update tasks for their courses" ON public.tasks
FOR UPDATE USING (
  EXISTS (
    SELECT 1 FROM public.courses
    WHERE courses.id = tasks.course_id
    AND courses.user_id = auth.uid()
  )
);

-- Policy: Users can delete tasks for their courses
CREATE POLICY "Users can delete tasks for their courses" ON public.tasks
FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM public.courses
    WHERE courses.id = tasks.course_id
    AND courses.user_id = auth.uid()
  )
);
```

## Database Schema Requirements

Make sure your tables have the following structure:

### Users table (optional - mainly using auth.users)

```sql
CREATE TABLE public.users (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  username TEXT,
  email TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Courses table

```sql
CREATE TABLE public.courses (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Tasks table

```sql
CREATE TABLE public.tasks (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  notes TEXT,
  course_id INTEGER REFERENCES public.courses(id) NOT NULL,
  due_date DATE,
  priority TEXT DEFAULT 'medium',
  completed TEXT DEFAULT 'Not Started',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Environment Variables Required

Make sure your `.env` file contains:

```
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
FLASK_SECRET_KEY=your_random_secret_key
FLASK_DEBUG=True
```

## Authentication Flow

1. User visits any protected route
2. If not authenticated, they're redirected to `/login`
3. User can login with email/password or GitHub OAuth
4. After authentication, they're redirected to the originally requested page
5. All API calls now include authentication context for RLS

## Testing

1. Start your Flask app: `python main.py`
2. Visit `http://localhost:5524/login`
3. Sign in with email/password or GitHub
4. Navigate to `/users`, `/courses`, or `/tasks`
5. All CRUD operations should work with proper RLS enforcement
