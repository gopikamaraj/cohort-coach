@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: CONFIGURATION VARIABLES
:: Update these values before running!
:: ==========================================
set PROJECT_ID=fln-cohort-coach
set SHEETS_BUCKET=fcc-build-app-sheets-bucket
set AUDIO_BUCKET=fcc-build-app-audio-bucket
set LOCATION=asia-south1
set SA_NAME=gcs-storage-admin
set KEY_FILE=gcs-key.json
set CORS_FILE=cors.json
set LIFECYCLE_FILE=lifecycle.json

echo ==========================================
echo Starting GCP Setup Script
echo ==========================================

:: 1. Set Active GCP Project
echo.
echo [1/5] Setting active project to %PROJECT_ID%...
call gcloud config set project %PROJECT_ID%

:: 2. Create Buckets with Uniform Access and Public Access Prevention
echo.
echo [2/5] Creating Storage Buckets...
call gcloud storage buckets create gs://%SHEETS_BUCKET% --location=%LOCATION% --uniform-bucket-level-access --public-access-prevention
call gcloud storage buckets create gs://%AUDIO_BUCKET% --location=%LOCATION% --uniform-bucket-level-access --public-access-prevention

:: 3. Create Service Account and Assign Roles
echo.
echo [3/5] Setting up Service Account and IAM roles...
call gcloud iam service-accounts create %SA_NAME% --display-name="GCS Object Admin SA"

set SA_EMAIL=%SA_NAME%@%PROJECT_ID%.iam.gserviceaccount.com

echo Granting Storage Object Admin on %SHEETS_BUCKET%...
call gcloud storage buckets add-iam-policy-binding gs://%SHEETS_BUCKET% --member="serviceAccount:%SA_EMAIL%" --role="roles/storage.objectAdmin"

echo Granting Storage Object Admin on %AUDIO_BUCKET%...
call gcloud storage buckets add-iam-policy-binding gs://%AUDIO_BUCKET% --member="serviceAccount:%SA_EMAIL%" --role="roles/storage.objectAdmin"

echo Downloading JSON key file to %KEY_FILE%...
call gcloud iam service-accounts keys create %KEY_FILE% --iam-account=%SA_EMAIL%

:: 4. Create and Apply CORS Configuration to Sheets Bucket
echo.
echo [4/5] Applying CORS configuration to %SHEETS_BUCKET%...
(
  echo [
  echo   {
  echo     "origin": ["*"],
  echo     "method": ["GET", "PUT", "POST", "HEAD", "DELETE", "OPTIONS"],
  echo     "responseHeader": ["Content-Type", "x-goog-resumable"],
  echo     "maxAgeSeconds": 3600
  echo   }
  echo ]
) > %CORS_FILE%

call gcloud storage buckets update gs://%SHEETS_BUCKET% --cors-file=%CORS_FILE%

:: 5. Create and Apply Lifecycle Rule to Sheets Bucket (97 days = 90-day retention + a week)
echo.
echo [5/5] Applying Lifecycle Rule to %SHEETS_BUCKET%...
(
  echo {
  echo   "rule": [
  echo     {
  echo       "action": {"type": "Delete"},
  echo       "condition": {
  echo         "age": 97
  echo       }
  echo     }
  echo   ]
  echo }
) > %LIFECYCLE_FILE%

call gcloud storage buckets update gs://%SHEETS_BUCKET% --lifecycle-file=%LIFECYCLE_FILE%

:: Clean up temporary policy files
if exist %CORS_FILE% del %CORS_FILE%
if exist %LIFECYCLE_FILE% del %LIFECYCLE_FILE%

echo.
echo ==========================================
echo Setup Completed Successfully!
echo Key File Saved as: %KEY_FILE%
echo ==========================================
pause