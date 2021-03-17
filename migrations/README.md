# For developers

## Setup
Create database tables
```bash
$ ./bin/run_migration.sh init
```

## DB Model Changed
Generate Migration Script

### Prerequisites
* Migration Setup is completed.
* env:DATABASE_SCHEMA is not set.
because DATABASE_SCHEMA is included in created index name.

### Generate Script
```bash
$ ./bin/run_migration.sh generate $file_suffix
```
e.g.) ./bin/run_migration.sh generate v1.0.0

### Reflect Local Environment
```bash
$ ./bin/run_migration.sh upgrade
```

### Notice
In the following cases, you will need to manually modify the autogenerated script.
* If column name changed, CREATE/DROP script is generated.   
That the existing column data will be erased.
* If column constrains changed, There is a possibility of failed the autogenerated script.  
For example, constrains changed Nullable to NotNull, etc