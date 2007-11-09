#! /bin/sh

for i in 1 2 3 4 5; do 
	./tpsai-py tp://ai$i:password@localhost --nosleep > ai$i.log 2>&1 &
done

tail -f ai1.log
