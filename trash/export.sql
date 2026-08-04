SELECT * FROM view_forecast_features_clean 
INTO OUTFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/forecasting_features_16col.csv' 
FIELDS TERMINATED BY ',' 
OPTIONALLY ENCLOSED BY '"' 
LINES TERMINATED BY '\n';
