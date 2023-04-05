Installing the AWS CLI software:  
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

General AWS CLI commands:
https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-commandstructure.html

The commands to access files in buckets using the CLI:  
https://awscli.amazonaws.com/v2/documentation/api/latest/reference/s3/index.html

### Configure AWS service
aws configure

AWS Access Key ID [None]: 

AWS Secret Access Key [None]: 

Default region name [None]: 

Default output format [None]: 

### check bucket contents
aws s3 ls pw-delivery-chalmersuniversity

aws s3 ls pw-delivery-chalmersuniversity/SE/

aws s3 ls pw-delivery-chalmersuniversity/SE/2019/

aws s3 ls pw-delivery-chalmersuniversity/SE/2019/06/

### Download data
aws s3 sync s3://pw-delivery-chalmersuniversity/SE/2019/06/ D://mad4abm/dbs/raw_data_se_2019/06/

aws s3 sync s3://pw-delivery-chalmersuniversity/SE/2019/07/ D://mad4abm/dbs/raw_data_se_2019/07/

aws s3 sync s3://pw-delivery-chalmersuniversity/SE/2019/07/25/locations-05-part0000.csv.gz D://mad4abm/dbs/raw_data_se_2019/07/25/locations-05-part0000.csv.gz

aws s3 sync s3://pw-delivery-chalmersuniversity/SE/2019/08/ D://mad4abm/dbs/raw_data_se_2019/08/

aws s3 sync s3://pw-delivery-chalmersuniversity/SE/2019/12/ D://mad4abm/dbs/raw_data_se_2019/12/
