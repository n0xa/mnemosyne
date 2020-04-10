function clear_collection(colname) {
    print('Working on collection ' + colname);
    print('* Before:');
    size = db[colname].totalSize()
    reccount = db[colname].count()
    print('* Total for ' + colname + ' in bytes: ' + size);
    print('* Total for ' + colname + ' in record count: ' + reccount);
    db[colname].deleteMany({});
    print('* After:');
    size = db[colname].totalSize()
    reccount = db[colname].count()
    print('* Total for ' + colname + ' in bytes: ' + size);
    print('* Total for ' + colname + ' in record count: ' + reccount);
    print('');
}

var db = connect('127.0.0.1:27017/mnemosyne');

var collections = ["counts", "daily_stats", "dork", "file", "hpfeed", "metadata", "session", "url"];

print('* Be patient while records delete, in large databases this call may take several minutes');

collections.forEach(clear_collection);

print('It may take some time for the deletions to reflect in the size...be patient!');
