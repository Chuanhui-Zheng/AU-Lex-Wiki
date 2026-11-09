# V2 acceptance checklist

The local V2 baseline is accepted when these checks pass:

- [ ] the Award manifest validates without duplicate codes;
- [ ] every Award has an official HTML source;
- [ ] available Pay Guides are separate `pay_guide` documents;
- [ ] PostgreSQL full-text Ask returns named Award evidence;
- [ ] an unrelated question is refused instead of answered from weak matches;
- [ ] `embedding` and `sparse_weights` remain empty in the text-only profile;
- [ ] the web application starts without importing BGE-M3.

The November 2026 capture currently contains 122 Awards, 121 Pay Guides,
13,323 Award chunks, and 1,121 Pay Guide chunks. The exact number can change
when the official catalogue publishes a new Award or Pay Guide.
