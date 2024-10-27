sudo apt-get update
sudo apt-get install stockfish

if [ ! -d "data/games" ]; then
    mkdir -p data/games 
    echo "data/games does not exist, downloading Lichess Elite Database from https://player.odycdn.com/v6/streams/b0f01856c521a5f782f8ce4ec6275054e71cf664/3a71ac.mp4?download=true"
    wget https://player.odycdn.com/v6/streams/b0f01856c521a5f782f8ce4ec6275054e71cf664/3a71ac.mp4?download=true -O data/games/lichess_elite_database.7z
    echo "Extracting Lichess Elite Database"
    7z x data/games/lichess_elite_database.7z -o./data/games/
    rm data/games/lichess_elite_database.7z
    echo "Done downloading Lichess Elite Database"
    
