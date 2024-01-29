if [ ! -f ./engine/stockfish ]; then
    echo "Stockfish engine not found. Downloading..."
    wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64-avx2.tar
    tar -xvf stockfish-ubuntu-x86-64-avx2.tar
    mv ./stockfish/stockfish-ubuntu-x86-64-avx2 ./engine/stockfish
    rm -rf ./stockfish
    rm stockfish-ubuntu-x86-64-avx2.tar
    echo "Stockfish engine downloaded."
fi
