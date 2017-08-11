/* ===== 1. Mean and median difference ===== */
SELECT
	-- Assuming we work with a PostgreSQL database version 9.6
	-- we can use the built-in function PERCENTILE_CONT to obtain the median value of the difference
	@ AVG(t.actual_eta) - AVG(t.predicted_eta) AS diff_mean
	@ ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY t.actual_eta)::numeric, 2) - ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY t.predicted_eta)::numeric, 2) AS diff_median
FROM
	trips AS t
		LEFT JOIN 
	cities AS c ON t.city_id = c.city_id	
WHERE
	-- Filter by city
	c.city_name IN ('Qarth', 'Meereen')
		-- We obtain the current datetime at Mexico City time zone and filter by the last 30 days
		AND CURRENT_TIMESTAMP::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City' - INTERVAL '30' DAY <= request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City';


/* ===== 2. Rate of successful rides ===== */
SELECT
  c.city_name, 
  EXTRACT(DOW FROM request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City') AS week_day,
  -- We create a new variable that represents if and rider completed her/his trip
  -- within the 7 day (= 168 hours) since s/he join Uber
  SUM(CASE 
      WHEN (t.status = 'completed') 
        -- Consider the actual datetime of a completed trip as the request datetime plus the actual estimated time of arrival
        AND (t.request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City' + INTERVAL t.actual_eta MINUTES <= e._ts::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City' + INTERVAL '7' DAYS) THEN 1
      ELSE 0
    END) / 
  -- Divided by the total of riders with the same conditions
  SUM(SELECT 
      COUNT(*)
    FROM 
      events
    WHERE 
      e.event_name = 'sign_up_success'
        AND c.city_name IN ('Qarth', 'Meereen')
        AND EXTRACT(YEAR FROM request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City') = 2016
        AND EXTRACT(WEEK FROM request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City') = 1) AS successful_ride
FROM 
  events AS e
    JOIN 
  trips AS t AS t ON e.rider_id = t.client_id
    LEFT JOIN
  cities AS c ON e.city_id = c.city_id  
WHERE 
  -- We only need riders who signing up successfully
  e.event_name = 'sign_up_success'
    -- Applying the correct filters...
    AND c.city_name IN ('Qarth', 'Meereen')
    AND EXTRACT(YEAR FROM request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City') = 2016
    AND EXTRACT(WEEK FROM request_at::TIMESTAMP WITH TIME ZONE AT TIME ZONE 'America/Mexico_City') = 1
GROUP BY
  -- To obtain the rate for both cities and each day of the first week in 2016
  c.city_name , week_day;

