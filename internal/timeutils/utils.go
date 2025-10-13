package timeutils

import "time"

// GetUTCStartOfCurrentMonth returns the start of the current UTC month
func GetUTCStartOfCurrentMonth() time.Time {
	now := time.Now().UTC()
	return time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
}

// GetUTCStartOfNextMonth returns the start of the next UTC month
func GetUTCStartOfNextMonth() time.Time {
	now := time.Now().UTC()
	return time.Date(now.Year(), now.Month()+1, 1, 0, 0, 0, 0, time.UTC)
}

// FormatForQuota returns month key in UTC format for quota storage
func FormatForQuota(t time.Time) string {
	return t.UTC().Format("2006-01")
}

// GetCurrentUTCMonthKey returns the current month key for quota operations
func GetCurrentUTCMonthKey() string {
	return FormatForQuota(time.Now())
}

// IsSameUTCMonth checks if two times are in the same UTC month
func IsSameUTCMonth(t1, t2 time.Time) bool {
	y1, m1, _ := t1.UTC().Date()
	y2, m2, _ := t2.UTC().Date()
	return y1 == y2 && m1 == m2
}

// GetUTCMonthStart returns the start of the month for the given time in UTC
func GetUTCMonthStart(t time.Time) time.Time {
	utc := t.UTC()
	return time.Date(utc.Year(), utc.Month(), 1, 0, 0, 0, 0, time.UTC)
}