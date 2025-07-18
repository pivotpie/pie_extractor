@echo off
echo 🚀 Setting up the database...

echo.
echo 🔧 Generating Prisma client...
npx prisma generate

if %errorlevel% neq 0 (
    echo ❌ Failed to generate Prisma client
    exit /b %errorlevel%
)

echo.
echo 🔄 Running database migrations...
npx prisma migrate dev --name init

if %errorlevel% neq 0 (
    echo ❌ Failed to run database migrations
    exit /b %errorlevel%
)

echo.
echo ✅ Database setup complete!
echo.
echo Next steps:
echo 1. Start the development server: npm run dev
echo 2. Access the application at http://localhost:3000
echo 3. Access Prisma Studio to view your database: npx prisma studio
