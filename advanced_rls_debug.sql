-- Advanced RLS Debugging - Let's check everything thoroughly

-- 1. Check if the policy was actually updated
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE tablename = 'courses';

-- 2. Check if RLS is properly enabled
SELECT schemaname, tablename, rowsecurity
FROM pg_tables 
WHERE tablename = 'courses';

-- 3. Test auth.uid() while authenticated (this should return your user ID)
SELECT auth.uid() as current_user_id;

-- 4. Check if there are any other policies interfering
SELECT * FROM pg_policies WHERE tablename = 'courses';

-- 5. Try inserting with auth.uid() directly (this bypasses any client-side issues)
INSERT INTO courses (name, description, user_id) 
VALUES ('Direct Auth Test', 'Testing with auth.uid()', auth.uid());

-- 6. If that works, clean it up
DELETE FROM courses WHERE name = 'Direct Auth Test';

-- 7. Alternative: Try temporarily disabling RLS to test if that's the issue
-- ALTER TABLE courses DISABLE ROW LEVEL SECURITY;
-- INSERT INTO courses (name, description, user_id) VALUES ('No RLS Test', 'Test without RLS', auth.uid());
-- ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
-- DELETE FROM courses WHERE name = 'No RLS Test';

-- 8. Check if there are any CHECK constraints or triggers that might be interfering
SELECT conname, consrc 
FROM pg_constraint 
WHERE conrelid = 'courses'::regclass AND contype = 'c';

-- 9. Check table permissions
SELECT grantee, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_name = 'courses' AND table_schema = 'public';
