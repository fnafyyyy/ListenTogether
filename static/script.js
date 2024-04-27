// Tworzymy połączenie z serwerem
        const socket = io.connect('http://127.0.0.1:5000');
        
        socket.emit(`files_request`);
        let audio;
        let filenames;
        let filepath;
        let duration;
        let interval;

        const time = document.getElementById(`time`);
        const filesList = document.getElementById(`filesList`);

        const changeAudio = (index, timestamp) => {
            if(audio){
                stop();
                reset();
            }
            audio = new Audio('../'+filepath+'/'+filenames[index]);
            setTimeout(() => {
                time.max = duration = audio.duration;
                time.value = audio.currentTime = timestamp;
            }, 100);
        }
        
        const reset = () => {
            if(audio){
                socket.emit('reset');
            }
        }

        const stop = () => {
            if (audio) {
                clearInterval(interval);
                audio.pause();
            }
        }

        const changeVolume = (event) => {
            let volume = event.target.value;
            if (audio) {
                audio.volume = volume;
            }
        }

        const playMusic = () => {
            if(!audio){
                socket.emit('play_music');
            }

            if(!audio.paused){
                socket.emit('stop_music');
            }else{
                socket.emit('play_music');
            }
        }

        socket.on(`requested_files`, (data) => {
            console.info(data);
            filenames = data.files;
            filepath = data.room_dir
    
            for(let i = 0; i<filenames.length;i++){
                filesList.innerHTML += `<li id="${i}">${filenames[i]}</li>`;
            }

            const listItems = document.querySelectorAll(`li`);
            listItems.forEach((item) => {
                item.addEventListener(`click`, () => {
                    socket.emit('changeAudio', item.id);
                })
            })

            changeAudio(data.file_id, data.timestamp);
        })

        socket.on('changeAudio', (id) => {
            changeAudio(id, 0);
        })

        // Nasłuchiwanie zdarzenia 'play'
        socket.on('play', function() {
            audio.play();
            interval = setInterval(() => {
                time.value++;
            }, 1000);
        });

        // Nasłuchiwanie zdarzenia 'stop'
        socket.on('stop', stop);

        socket.on(`reset`,() => {
            audio.currentTime = 0;
            time.value = 0;
        })

        socket.on(`getTime`,() => {
            stop()
            socket.emit(`requestedTime`, time.value)
        })

        socket.on('update_users', function(userCount) {
            // Aktualizacja liczby użytkowników
            document.getElementById('userCount').innerText = userCount;
        });

        // Nasłuchiwanie zdarzenia 'volume'
        socket.on('volume', function(volume) {
            // Sprawdzamy, czy obiekt audio istnieje
            if (audio) {
                // Ustawiamy głośność
                audio.volume = volume;
            }
        });

        