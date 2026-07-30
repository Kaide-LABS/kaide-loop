# Baby PRD

## TL;DR
A saved transcript of an Islamic lecture I couldn't attend live becomes an accurate, structured summary -- segmented, faithful to the source, with rulings and citations preserved exactly as spoken -- so I can review what was taught without having to watch the recording. -- 2 acceptance criterion(ia), 1 scope edge(s) named.

## Problem statement
A saved transcript of an Islamic lecture I couldn't attend live becomes an accurate, structured summary -- segmented, faithful to the source, with rulings and citations preserved exactly as spoken -- so I can review what was taught without having to watch the recording.

## Acceptance criteria
- Feed it a saved lecture transcript containing at least one deliberately ambiguous/garbled passage. Check, by direct inspection: (1) segment boundaries match an independently human-marked reference within [tolerance] / a reviewer agrees each segment is coherent; (2) every ruling is phrased as reported speech attributed to the speaker, never asserted as fact; (3) every citation string-matches the transcript verbatim or is omitted -- checked against the transcript, not external canon; (4) the deliberately-ambiguous passage is explicitly flagged, not smoothed over.
- Watch-out: this is being judged specifically on trustworthiness for religious content, not just summarization quality. Never let the model fabricate -- if it's not confident about a ruling or a citation, it must flag the passage rather than smooth it into something plausible-sounding. A subtly wrong ruling or a garbled citation is a worse failure than an incomplete summary.

## Scope edges
- **out**: Live Zoom integration is out of scope for now -- joining meetings, audio capture, the speech-to-text API call, and auth are deferred to a later, separate build. This project takes a saved transcript file as input, not live audio. Tripwire: any dependency on Zoom's SDK, an STT provider, or a network call to join a meeting appearing in this repo means scope has crept -- that code belongs in the later integration build, not here. -- user-stated

## Boundary
This project builds only the deterministic core: ingesting a saved transcript file and producing a structured, citation-faithful summary -- segmentation, the summarization pipeline, the output schema, and the correctness rules governing rulings and citations. Anything requiring a live third-party surface (Zoom SDK, an STT provider, meeting-join auth, or any network call to capture live audio) is out of scope for this build and belongs to a later, separate integration project.
