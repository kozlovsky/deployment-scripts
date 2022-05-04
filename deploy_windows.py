"""
This script fetches the latest build executable for Win64 from Jenkins
and installs it. Note that it expects the following environment
variable:
- JENKINS_JOB_URL : Jenkins job which builds the Debian package
- BUILD_TYPE : Build type [Win64, Win32, Linux, MacOS]
- WORKSPACE : Jenkins workspace (set by jenkins itself)
"""
import subprocess
import time
import os

from deployment_utils import check_sha256_hash, fetch_latest_build_artifact, init_sentry, print_and_exit, \
    tribler_is_installed


if __name__ == '__main__':
    init_sentry()

    # Step 1: fetch the latest Tribler installer from Jenkins
    build_type = os.environ.get('BUILD_TYPE', 'Win64')
    job_url = os.environ.get('JENKINS_JOB_URL', None)
    if not job_url:
        print_and_exit('JENKINS_JOB_URL is not set')

    print('Fetching latest artifacts')
    INSTALLER_FILE, HASH = fetch_latest_build_artifact(job_url, build_type)
    print('Artifacts are fetched')

    # Step 2: check SHA256 hash
    if HASH and not check_sha256_hash(INSTALLER_FILE, HASH):
        print("SHA256 of file does not match with target hash %s, we retry to download it" % HASH)
        INSTALLER_FILE, HASH = fetch_latest_build_artifact(job_url, build_type)
        if HASH and not check_sha256_hash(INSTALLER_FILE, HASH):
            print_and_exit("Download seems to be really broken, bailing out")

    # Add waiting time before installer start to be sure that deinstaller finishes possible background tasks
    print('Pre-install pause')
    time.sleep(10)

    # Step 3: run the installer
    success_install = False
    for i in range(10):
        print('Installing Tribler' if not i else 'Try again...')
        start_time = time.time()

        completed_process = subprocess.run([INSTALLER_FILE, "/S"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff_time = time.time() - start_time

        print('Tribler %s installation finishes in %s seconds' % (build_type, diff_time), end=' ')

        if completed_process.returncode != 0:
            print(f'with error code {completed_process.returncode}.\n'
                  f'Stdout:\n{completed_process.stdout}\n\nStderr:\n{completed_process.stderr}\n\n')
        else:
            # Step 4: check whether Tribler has been correctly installed
            time.sleep(3)
            if tribler_is_installed():
                print('successfully')
                success_install = True
                break
            else:
                print('without an error, but Tribler is not installed')

        time.sleep(10)

    if not success_install:
        print_and_exit('Tribler has not been correctly installed')
