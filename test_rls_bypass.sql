-- Temporary RLS Bypass Test
-- Run this in Supabase SQL Editor to test if RLS is the only issue

-- 1. Temporarily disable RLS on courses table
ALTER TABLE courses DISABLE ROW LEVEL SECURITY;

-- 2. Try inserting a test course (this should work now)
INSERT INTO courses (name, description, user_id) 
VALUES ('RLS Bypass Test', 'Testing without RLS', '4c607249-d43b-4891-8f71-d440cdfefb9c');

-- 3. Check if it was inserted
SELECT * FROM courses WHERE name = 'RLS Bypass Test';

-- 4. Clean up the test
DELETE FROM courses WHERE name = 'RLS Bypass Test';

-- 5. Re-enable RLS
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

-- This test will confirm if RLS is the issue or if there are other constraints
