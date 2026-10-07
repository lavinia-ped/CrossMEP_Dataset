# validate_pptx

Checks every XML part of a .pptx against the OOXML schemas (Apache POI's
XMLBeans bindings). A part that fails here is one PowerPoint answers with its
"repair" prompt, usually dropping the offending shape.

    cd scripts/validate_pptx
    mvn -q dependency:copy-dependencies -DoutputDirectory=lib
    rm lib/poi-ooxml-lite-*.jar
    javac -cp "lib/*" Validate.java
    java -cp "lib/*:." Validate ../../docs/CrossMEP_CIBW78_talk.pptx

Expected output for the released deck: `TOTAL ERRORS 0`. The deck builder
(`docs/deck/build_deck.js`) repairs the known pptxgenjs 4.0.1 violations in its
post-processing step; this script is the check that it did.
