import subprocess;
from g2p_en import G2p

g2p = G2p()

test_phrase = "Hello Andy. The linguistic system is online and fully operational."

phonemes = g2p(test_phrase)
print(f"Original Text: {test_phrase}")
print(f"Phonetic Translation: {phonemes}\n")

print("Triggering espeak audio...")
subprocess.run(['espeak', test_phrase])

