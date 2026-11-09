# HUST schema correction before any HUST score

The first attempt stopped before fitting because five publisher files are shorter
than the nominal ten seconds: B602 has319211 samples, B604382456, B800338322,
B802389691, B804209000. These files match publisher SHA256; do not pad, repeat,
drop, or treat them as corrupt. Use every complete1s window after discarding the
first1s, up to10s total. All other settings of PROTOCOL_V_EXTERNAL remain frozen.
Record native duration and number of windows per file. Average per recording/class
equally, so short recordings do not receive less evaluation weight. At least3
complete fault windows and5healthy windows required. No HUST fault scores existed
when this correction was made. KAIST code and running experiment stay unchanged.
