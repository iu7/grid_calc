#!/bin/bash

echo "#include <iostream>" > test.cpp
echo "int main(){std::cout << \"HELLO WORLD!\" << std::endl;}" >> test.cpp
g++ test.cpp -o a.out

set -v

curl @"localhost:50002/static"               -X POST -F file=@a.out; echo
curl @"localhost:50002/static?path=1\2\3\4"  -X POST -F file=@a.out; echo

curl @"localhost:50002/static/a.out"         -X GET > a__.out      ; echo
chmod +x a__.out                                                   ; echo
./a__.out                                                          ; echo

curl @"localhost:50002/static/1\2\3\4\a.out" -X GET > a_.out       ; echo
chmod +x a_.out                                                    ; echo
./a_.out                                                           ; echo

curl @"localhost:50002/static/a.out"         -X DELETE             ; echo
curl @"localhost:50002/static/1\2\3\4\a.out" -X DELETE             ; echo

curl @"localhost:50002/static/a.out"         -X DELETE             ; echo
curl @"localhost:50002/static/1\2\3\4\a.out" -X DELETE             ; echo

curl @"localhost:50002/static/a.out"         -X GET                ; echo
curl @"localhost:50002/static/1\2\3\4\a.out" -X GET                ; echo

rm a*.out test.cpp