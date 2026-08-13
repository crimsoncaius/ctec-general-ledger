Durable background-job progress: integrity checks, trial balance runs, migration trials.

```jsx
<ProgressBar label="Integrity check" status="running" value={64} />
```

Progress reflects the persisted server value, so it survives navigation. Never imply that leaving the page cancels the job.
