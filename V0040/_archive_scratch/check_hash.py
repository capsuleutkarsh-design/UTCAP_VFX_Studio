import bcrypt

admin_hash = b"$2b$12$.QDyrGeLQ2ILULHNIvUOqeCdFVhJC6SNn99BdlZyYixfZU0q9saH6"
emp_hash = b"$2b$12$UWmAINX5UG6Yzsa5q6Ypret/DdnIGz85wxfAupnBQfQBCh1J2DrlC"

print('Admin matches admin123:', bcrypt.checkpw(b'admin123', admin_hash))
print('EMP0012 matches admin123:', bcrypt.checkpw(b'admin123', emp_hash))
