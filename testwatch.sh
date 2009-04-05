#! /bin/sh

for i in 1 2 3 4 5; do 
	echo -n "ai$i "
	if grep Exiting ai$i.log; then
		echo "AI is dead"
		continue
	fi
	number=$((`cat ai$i.log | wc -l` - `grep -n "Status" ai$i.log | sed -e's/.*log://' -e's/:.*//' | tail -1` + 1 )); tail -n $number ai$i.log | head -n $(($number -2))
done
