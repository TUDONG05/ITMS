# Responsive table and overlay audit

Date: 2026-11-27. Status: implemented; final build, lint and formatting checks passed.
The evaluation manager table omitted `responsive-card-table` and cell labels, squeezing seven columns into mobile content; the broader audit also exposed an exact-768px breakpoint mismatch and internship table clipping on tablets.
Applied responsive corrections across users, requests, documents, Mentor tasks, training, learning, internship table scrolling, and evaluation overlays; reused card layouts and stacked filters where appropriate.
The choice was to correct table/overlay behavior and breakpoint coverage rather than hide more overflow: clipping would conceal inaccessible content instead of fixing its layout.
The frustrating part is that an existing mobile pattern still left gaps at real viewport boundaries. Lesson: test exactly at the breakpoint and include tablet widths, not just representative phones and desktops.
Measured Admin screens at 320/375/768/1024/1440px and Mentor and Intern screens at 320/375/768/1024px; verified drawer bounds at 375px. Rechecked Mentor cards at 768px and internship table containment at 320/768/1024px after fixes. These are screen measurements, not a claim that every interaction was exercised.
Tests: 30 Admin/evaluation and 21 training/learning tests pass; tasks have 17 passing tests and two known baseline failures, confirmed again with the original CSS.
Final build, lint and formatting checks pass; warnings cover the initial bundle budget, training stylesheet budget, and `jszip` CommonJS dependency.
Frontend and backend remain running locally. Changes are prepared for a pull request into develop; no deployment was requested.
