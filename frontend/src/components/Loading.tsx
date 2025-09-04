import React from "react";

export function Spinner() { return <div className="spin" aria-label="loading" />; }

export function Skeleton({ lines = 3 }:{ lines?: number }) {
  return (
    <div className="skel">
      {Array.from({length: lines}).map((_,i)=> <div key={i} className="skel-line" />)}
    </div>
  );
}
