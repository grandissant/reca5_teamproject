document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    console.log('현재 경로:', currentPath);

    // join_membership 페이지 관련 기능
    if (currentPath.includes('join_membership')) {
        console.log('join_membership 페이지에서 실행됩니다.');
        const joinForm = document.getElementById('joinForm');
        const fileInput = document.getElementById('imageUploadInput');
        const messageBox = document.getElementById('messageBox');
        const nameInput = document.getElementById('user_name');
        const passwordInput = document.getElementById('user_password');
        const subjectInput = document.getElementById('subject');

        // 프로필 이미지 미리보기 함수
        function previewImage(inputElement) {
            console.log('previewImage 함수가 호출되었습니다.');
            if (inputElement.files && inputElement.files[0]) {
                console.log('파일이 선택되었습니다.');
                const reader = new FileReader();
                reader.onload = function(e) {
                    console.log('파일이 읽혀졌습니다.');
                    const imagePreview = document.getElementById('imagePreview');
                    if (imagePreview) {
                        const img = imagePreview.querySelector('img');
                        if (img) {
                            console.log('기존 이미지 태그가 발견되었습니다.');
                            img.src = e.target.result;
                            img.classList.remove('default-icon'); // 기본 아이콘 클래스 제거
                        } else {
                            console.log('새로운 이미지 태그를 생성합니다.');
                            const newImg = document.createElement('img');
                            newImg.src = e.target.result;
                            newImg.alt = "사진 업로드 미리보기";
                            imagePreview.appendChild(newImg);
                        }
                    } else {
                        console.error('imagePreview 요소를 찾을 수 없습니다.');
                    }
                };
                reader.readAsDataURL(inputElement.files[0]);
            } else {
                console.log('파일이 선택되지 않았습니다.');
            }
        }

        // 이미지 업로드 입력 요소에 이벤트 리스너 추가
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                console.log('파일 입력 요소의 change 이벤트가 발생했습니다.');
                previewImage(this);
            });
        } else {
            console.error('File input element not found');
        }

        // 회원가입 폼 이벤트 리스너
        if (joinForm) {
            joinForm.addEventListener('submit', function(event) {
                event.preventDefault(); // 폼 전송 중지

                const formData = new FormData(joinForm);

                // 회원가입 요청 보내기
                fetch('/join_membership', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (response.ok) {
                        return response.text(); // HTML로 응답 처리
                    } else {
                        throw new Error('회원가입에 실패하였습니다.'); // 서버 에러 처리
                    }
                })
                .then(html => {
                    // 응답 내용에 '성공' 메시지가 포함되어 있는지 확인 (서버 측 구현에 따라 조정 필요)
                    if (html.includes('회원가입이 완료되었습니다.')) {
                        alert('회원가입에 성공하였습니다.');
                        messageBox.innerHTML = html; // 성공한 경우, 응답을 페이지에 표시
                    } else {
                        throw new Error('회원가입에 실패하였습니다.'); // 내용이 성공 메시지를 포함하지 않는 경우
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    // alert(error.message);
                    messageBox.innerText = error.message; // 에러 메시지 표시
                });
            });
        }
    }

    // register 페이지 관련 기능
    if (currentPath.includes('register')) {
        console.log('register 페이지에서 실행됩니다.');
        const attendanceForm = document.getElementById('attendanceForm');
        const attendanceTableBody = document.getElementById('attendanceTableBody');
        const openBtn = document.getElementById('openBtn');
        const closeBtn = document.getElementById('closeBtn');
        const captureBtn = document.getElementById('captureBtn');
        let streamVideo;

        // 본인 확인 상태를 추적하는 변수 추가
        let isVerified = false;

        // 카메라 관련 기능
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Media Device not supported");
        } else {
            openBtn.addEventListener('click', openCamera);
            closeBtn.addEventListener('click', closeCamera);
            captureBtn.addEventListener('click', captureAndCheckAttendance);
        }

        function openCamera() {
            closeCamera();
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    streamVideo = stream;
                    const cameraView = document.getElementById("cameraview");
                    cameraView.srcObject = stream;
                    cameraView.play();
                })
                .catch(error => {
                    console.error('카메라 접근 권한이 거부되었습니다.', error);
                    alert(`카메라 접근 권한이 필요합니다. 오류: ${error.name} - ${error.message}`);
                });
        }

        function closeCamera() {
            if (streamVideo) {
                const tracks = streamVideo.getTracks();
                tracks.forEach(track => track.stop());
                streamVideo = null;
            }
        }

        function captureAndCheckAttendance() {
            const video = document.getElementById("cameraview");
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const context = canvas.getContext("2d");
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const imageData = canvas.toDataURL('image/jpeg');

            console.log('전송할 데이터:', { image: imageData });

            fetch('/attendance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image: imageData })
            })
            .then(response => response.json())  // response.text()에서 response.json()으로 변경
            .then(data => {
                console.log('서버 응답 데이터:', data);
                const log = document.getElementById('attendanceLog');
                const p = document.createElement('p');
                p.textContent = data.message;
                log.appendChild(p);

                // 새로 추가: 본인 확인 상태 설정 및 출석 버튼 활성화/비활성화
                isVerified = data.verified === true;
                document.getElementById('attendanceButton').disabled = !isVerified;
                
                if (isVerified) {
                    alert("본인 확인이 완료되었습니다. 출석 버튼을 눌러주세요.");
                } else {
                    alert("본인 확인에 실패했습니다. 다시 시도해주세요.");
                }
            })
            .catch(error => console.error('Error:', error));
        }

        // 사용자 이름을 서버로부터 가져와서 설정
        if (attendanceForm) {
            fetch('/get_username')
                .then(response => response.text())
                .then(username => {
                    document.getElementById('username').value = username;
                })
                .catch(error => console.error('Error:', error));

            // 출석 폼 이벤트 리스너
            attendanceForm.addEventListener('submit', function(event) {
                event.preventDefault();

                // 새로 추가: 본인 확인 상태 확인
                if (!isVerified) {
                    alert("먼저 본인 확인을 해주세요.");
                    return;
                }

                var username = document.getElementById('username').value;
                var time = new Date().toLocaleTimeString();
                var message = document.getElementById('message').value;

                document.getElementById('time').value = time;

                fetch('/attendance', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: username,
                        time: time,
                        message: message
                    })
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.status === '출석 완료됨') {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${time}</td>
                            <td>${username}</td>
                            <td>${message}</td>
                        `;
                        attendanceTableBody.appendChild(row);

                        // 새로 추가: 출석 완료 후 상태 초기화
                        isVerified = false;
                        document.getElementById('attendanceButton').disabled = true;
                    }
                })
                .catch(error => console.error('Error:', error));
            });

            // 초기 로딩 시 기존 출석 기록을 불러와서 테이블에 표시
            fetch('/attendance/records')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.text();
                })
                .then(data => {
                    console.log('Fetched records:', data);
                    if (data.trim() === '') {
                        console.error('No records found');
                        return;
                    }
                    const records = data.split('\n');
                    attendanceTableBody.innerHTML = '';
                    records.forEach(record => {
                        if (record.trim() !== '') {
                            const [timestamp, userAndMessage] = record.split(' - ');
                            const [username, message] = userAndMessage.split(': ');
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${timestamp}</td>
                                <td>${username}</td>
                                <td>${message}</td>
                            `;
                            attendanceTableBody.appendChild(row);
                        }
                    });
                })
                .catch(error => {
                    console.error('Error fetching records:', error);
                    console.error('Error message:', error.message);
                });
        }

        // 새로 추가: 페이지 로드 시 출석 버튼 비활성화
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('attendanceButton').disabled = true;
        });
    }

    // 로그인 폼 이벤트 리스너
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(loginForm);

            // 폼 데이터 디버깅
            for (var pair of formData.entries()) {
                console.log(pair[0]+ ': ' + pair[1]);
            }

            fetch('/login', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                const contentType = response.headers.get('Content-Type');
                if (response.ok && contentType.includes('text/html')) {
                    return response.text();  // HTML로 응답 처리
                } else {
                    throw new Error('Unexpected content type or error occurred');
                }
            })
            .then(html => {
                document.body.innerHTML = html;  // 서버에서 받은 HTML을 페이지에 표시
            })
            .catch(error => {
                console.error('로그인 요청 중 에러 발생', error);
                alert('로그인 처리 중 오류가 발생했습니다.');
            });
        });
    }
});
